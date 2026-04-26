"""Vercel Python serverless function: POST /api/score (chat endpoint).

This is a real conversational agent. The frontend POSTs the running
message history; the LLM drives the conversation, asking the user about
how many passwords they manage and the age of the oldest one. Once it
has both, it calls the ``compute_health_score`` tool — and only then
does the function return a result payload (otherwise it returns the
next assistant message).

Constitution III: every tool input is validated by Pydantic.
Constitution IV: every error returns ``{"code": ..., "message": ...}``.
Constitution VII: every successful response is structured JSON.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Final, Literal

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

# ---------------------------------------------------------------------------
# Error envelope (Constitution IV + VII)
# ---------------------------------------------------------------------------

INVALID_INPUT: Final[str] = "INVALID_INPUT"
AGENT_TIMEOUT: Final[str] = "AGENT_TIMEOUT"
AGENT_FORMAT_ERROR: Final[str] = "AGENT_FORMAT_ERROR"
RATE_LIMITED: Final[str] = "RATE_LIMITED"
INTERNAL_ERROR: Final[str] = "INTERNAL_ERROR"

_DEFAULT_MESSAGES: Final[dict[str, str]] = {
    INVALID_INPUT: "I didn't quite catch that — could you give me a number?",
    AGENT_TIMEOUT: "That took longer than expected. Want to try once more?",
    AGENT_FORMAT_ERROR: "I had trouble putting that together. Mind sending it again?",
    RATE_LIMITED: "You're moving fast! Give it a moment and try again.",
    INTERNAL_ERROR: "Something hiccuped on our side. Please try again in a bit.",
}


def friendly_message_for(code: str) -> str:
    """Return the default friendly user-safe message for an error code."""
    return _DEFAULT_MESSAGES.get(code, _DEFAULT_MESSAGES[INTERNAL_ERROR])


def error_response(code: str, status: int, message: str | None = None) -> JSONResponse:
    """Build a JSONResponse following the universal error envelope."""
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message or friendly_message_for(code)},
    )


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class Band(str, Enum):
    """Score band used for color coding the result card."""

    HEALTHY = "HEALTHY"
    OKAY = "OKAY"
    CRITICAL = "CRITICAL"


class ChatMessage(BaseModel):
    """One turn of the conversation."""

    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2_000)


class ChatRequest(BaseModel):
    """Inbound chat payload."""

    model_config = ConfigDict(extra="forbid")
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class ToolArgs(BaseModel):
    """Arguments the LLM must supply to ``compute_health_score``."""

    model_config = ConfigDict(extra="forbid")
    password_count: int = Field(ge=0, le=10_000)
    oldest_password_age_months: int = Field(ge=0, le=600)


class Recommendation(BaseModel):
    """A single actionable fix."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)


# ---------------------------------------------------------------------------
# Deterministic scoring (research §R5)
# ---------------------------------------------------------------------------

_HEALTHY_FLOOR = 80
_OKAY_FLOOR = 50
_AGE_WEIGHT = 0.50
_COUNT_OVERAGE_WEIGHT = 0.20
_COUNT_COMFORT_THRESHOLD = 50


def _clamp(value: float, lo: int, hi: int) -> int:
    """Clamp a number into the closed integer range ``[lo, hi]``."""
    return max(lo, min(hi, int(round(value))))


def band_for(score: int) -> Band:
    """Return the band a score belongs to per spec thresholds."""
    if score >= _HEALTHY_FLOOR:
        return Band.HEALTHY
    if score >= _OKAY_FLOOR:
        return Band.OKAY
    return Band.CRITICAL


def compute_score(password_count: int, oldest_password_age_months: int) -> tuple[int, Band]:
    """Compute a deterministic 0..100 score and the matching band."""
    count_overage = max(0, password_count - _COUNT_COMFORT_THRESHOLD)
    raw = (
        100
        - _COUNT_OVERAGE_WEIGHT * count_overage
        - _AGE_WEIGHT * oldest_password_age_months
    )
    score = _clamp(raw, 0, 100)
    return score, band_for(score)


# ---------------------------------------------------------------------------
# Recommendation catalogue
# ---------------------------------------------------------------------------

Predicate = Callable[[int, int, int, Band], bool]


@dataclass(frozen=True)
class _CatalogueEntry:
    """A single recommendation candidate."""

    id: str
    title: str
    impact_weight: int
    applies_when: Predicate


def _always(_c: int, _m: int, _s: int, _b: Band) -> bool:
    """Predicate matching every (inputs, score)."""
    return True


_CATALOGUE: tuple[_CatalogueEntry, ...] = (
    _CatalogueEntry(
        id="START_FIRST_PASSWORD",
        title="Save your first password to the manager — you've got a great place to start.",
        impact_weight=110,
        applies_when=lambda c, m, s, b: c == 0,
    ),
    _CatalogueEntry(
        id="CELEBRATE_HEALTHY",
        title="Keep up the routine — a quick monthly check keeps you in the green.",
        impact_weight=105,
        applies_when=lambda c, m, s, b: b is Band.HEALTHY,
    ),
    _CatalogueEntry(
        id="ROTATE_OLDEST_PASSWORD",
        title="Replace your oldest password with a fresh one — that's the biggest win.",
        impact_weight=100,
        applies_when=lambda c, m, s, b: m >= 12,
    ),
    _CatalogueEntry(
        id="ENABLE_MFA_EVERYWHERE",
        title="Turn on two-factor wherever it's offered — it stops most account takeovers.",
        impact_weight=90,
        applies_when=_always,
    ),
    _CatalogueEntry(
        id="REMOVE_REUSED_PASSWORDS",
        title="Find any reused passwords and give each account its own.",
        impact_weight=85,
        applies_when=lambda c, m, s, b: c >= 5,
    ),
    _CatalogueEntry(
        id="ROTATE_AGED_PASSWORDS",
        title="Refresh anything older than two years — quick rotations add up.",
        impact_weight=70,
        applies_when=lambda c, m, s, b: m >= 24,
    ),
    _CatalogueEntry(
        id="USE_PASSPHRASES",
        title="Lean on long passphrases for the accounts you log in to most.",
        impact_weight=55,
        applies_when=_always,
    ),
    _CatalogueEntry(
        id="PRUNE_UNUSED_ACCOUNTS",
        title="Close or unlink old accounts you don't use — fewer doors to defend.",
        impact_weight=45,
        applies_when=lambda c, m, s, b: c >= 60,
    ),
    _CatalogueEntry(
        id="REVIEW_RECOVERY_OPTIONS",
        title="Double-check recovery emails and phone numbers on key accounts.",
        impact_weight=40,
        applies_when=_always,
    ),
    _CatalogueEntry(
        id="ENABLE_BREACH_ALERTS",
        title="Switch on breach alerts so you hear about leaks early.",
        impact_weight=35,
        applies_when=_always,
    ),
)


def pick_recommendations(
    password_count: int,
    oldest_password_age_months: int,
    score: int,
    band: Band,
    *,
    limit: int = 5,
) -> list[Recommendation]:
    """Select the top recommendations for a given check."""
    matched = [
        e
        for e in _CATALOGUE
        if e.applies_when(password_count, oldest_password_age_months, score, band)
    ]
    matched.sort(key=lambda e: e.impact_weight, reverse=True)
    return [Recommendation(id=e.id, title=e.title) for e in matched[:limit]]


# ---------------------------------------------------------------------------
# Agent prompt + tool spec
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a warm, concise password-health coach in a chat
app. Your job is to learn two things from the user:
  1. Roughly how many passwords they manage right now (an integer 0..10000).
  2. The age of their oldest password, normalized to whole months
     (0..600). Accept casual answers like "a few years", "since 2018",
     "maybe 18 months" — convert to months yourself.

Conversation rules:
- Stay encouraging in EVERY band. Never use words like "fail", "danger",
  "hacked", "stupid", "shame", or "idiot".
- Keep replies to 1–2 short sentences.
- If the user types something off-topic (asks what the app does, says
  hello, asks general security questions), answer briefly in one
  sentence, then steer back to the two questions.
- If a number is ambiguous ("a lot", "many"), ask politely for a rough
  estimate.
- Never ask for the user's actual passwords, account names, or any
  personal info beyond the two numbers.

When — and only when — you have confident integer values for BOTH, call
the ``compute_health_score`` tool with them. Do not call the tool until
you have both values. Do not invent values. Do not call the tool more
than once per session.

After the tool returns its result, the runtime will end the turn for
you with a final encouraging message — you don't need to write one.
"""

_TOOL_SPEC: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "compute_health_score",
            "description": (
                "Compute the user's password-health score once you have "
                "confirmed integer values for password_count and "
                "oldest_password_age_months."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["password_count", "oldest_password_age_months"],
                "properties": {
                    "password_count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 10000,
                        "description": "Number of passwords the user manages.",
                    },
                    "oldest_password_age_months": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 600,
                        "description": "Age in whole months of the oldest password.",
                    },
                },
            },
        },
    }
]

# Final-message instruction sent after the tool result lands.
_FINAL_MESSAGE_INSTRUCTION = (
    "Now write a short (1-2 sentence), warm, encouraging message for the "
    "user that acknowledges their score and points to the top recommendation "
    "as a friendly next step. Do not list every recommendation — the UI shows "
    "them already. Do not include the numeric score in the text; the UI shows "
    "that too."
)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

logger = logging.getLogger("agent.score")

_AGENT_MODEL = "gpt-4o-mini"
_AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "20"))

app = FastAPI(title="Password Manager Health Agent", version="0.2.0")

_allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin] if _allowed_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


async def _run_chat_turn(messages: list[ChatMessage]) -> dict[str, Any]:
    """Run one conversation turn against OpenAI and return a typed reply.

    Returns a dict shaped like one of:
      ``{"type": "message", "content": str}``
      ``{"type": "result", "score": int, "band": str,
         "recommendations": [...], "password_count": int,
         "oldest_password_age_months": int, "message": str}``
    """
    from openai import AsyncOpenAI  # local import; SDK is heavy

    client = AsyncOpenAI()

    chat_messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[{"role": m.role, "content": m.content} for m in messages],
    ]

    logger.info("calling openai (turn=%d)", len(messages))
    first = await client.chat.completions.create(
        model=_AGENT_MODEL,
        messages=chat_messages,
        tools=_TOOL_SPEC,
        tool_choice="auto",
        temperature=0.4,
    )
    choice = first.choices[0].message
    tool_calls = choice.tool_calls or []
    logger.info("openai turn1: content_len=%d tool_calls=%d",
                len(choice.content or ""), len(tool_calls))

    # No tool call -> the LLM is still gathering info. Return its reply.
    if not tool_calls:
        return {"type": "message", "content": (choice.content or "").strip() or
                "Could you tell me how many passwords you have right now?"}

    # The LLM decided it has both inputs. Validate the call.
    call = tool_calls[0]
    try:
        raw_args = json.loads(call.function.arguments or "{}")
        args = ToolArgs.model_validate(raw_args)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("tool args invalid: %s", exc)
        return {
            "type": "message",
            "content": (
                "Hmm, I need a clearer number. Could you tell me roughly "
                "how many passwords you have, and how old the oldest one is?"
            ),
        }

    score, band = compute_score(args.password_count, args.oldest_password_age_months)
    recommendations = pick_recommendations(
        args.password_count, args.oldest_password_age_months, score, band
    )

    # Build the follow-up call. The OpenAI API requires an assistant message
    # with `content` AND `tool_calls` fields (`content` can be None) before
    # the matching `tool` message. We reconstruct it explicitly so the
    # message is well-formed regardless of SDK version.
    assistant_with_tool_call: dict[str, Any] = {
        "role": "assistant",
        "content": choice.content,  # may be None — OpenAI accepts that
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
        ],
    }

    follow_up = await client.chat.completions.create(
        model=_AGENT_MODEL,
        messages=[
            *chat_messages,
            assistant_with_tool_call,
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(
                    {
                        "score": score,
                        "band": band.value,
                        "top_recommendation": (
                            recommendations[0].title if recommendations else None
                        ),
                    }
                ),
            },
            {"role": "system", "content": _FINAL_MESSAGE_INSTRUCTION},
        ],
        temperature=0.6,
    )
    final = (follow_up.choices[0].message.content or "").strip() or (
        "Nice work — you're on the way. Try the top fix below as your next step."
    )
    logger.info("openai turn2 done: msg_len=%d", len(final))

    return {
        "type": "result",
        "score": score,
        "band": band.value,
        "recommendations": [r.model_dump() for r in recommendations],
        "password_count": args.password_count,
        "oldest_password_age_months": args.oldest_password_age_months,
        "message": final,
    }


@app.post("/")
async def post_chat(request: Request) -> Any:
    """Handle the POST. Vercel mounts this app at ``/api/score``."""
    try:
        raw = await request.json()
    except Exception:
        return error_response(INVALID_INPUT, status=400)

    try:
        payload = ChatRequest.model_validate(raw)
    except ValidationError:
        return error_response(INVALID_INPUT, status=400)

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY missing")
        return error_response(INTERNAL_ERROR, status=500)

    try:
        result = await asyncio.wait_for(
            _run_chat_turn(payload.messages), timeout=_AGENT_TIMEOUT_SECONDS
        )
    except asyncio.TimeoutError:
        return error_response(AGENT_TIMEOUT, status=504)
    except Exception:
        logger.exception("agent invocation failed")
        return error_response(INTERNAL_ERROR, status=500)

    return result


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_request, _exc) -> JSONResponse:
    """Catch-all that maps stray exceptions to the friendly envelope."""
    return error_response(INTERNAL_ERROR, status=500)
