"""Vercel Python serverless function: POST /api/score.

Single-file FastAPI app that exposes the password-health agent. Vercel
routes any request to ``/api/score`` to this file's ``app`` (it strips the
``/api/score`` prefix), so the FastAPI route is mounted at ``/``.

Constitution III: every input is validated by Pydantic. Constitution IV:
every error returns ``{"code": ..., "message": ...}``. Constitution VII:
every successful response is a typed JSON body matching :class:`AgentScoreResponse`.

The whole agent (schemas, scoring, recommendations, prompts, route) is
inlined here on purpose: Vercel's Python runtime treats every top-level
``.py`` in ``api/`` as a separate function, so cross-file imports under
``api/`` are fragile. Keeping it in one file is bullet-proof.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Final

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
# Pydantic schemas (mirrors contracts/agent-score.schema.json)
# ---------------------------------------------------------------------------


class Band(str, Enum):
    """Score band used for color coding the result card."""

    HEALTHY = "HEALTHY"
    OKAY = "OKAY"
    CRITICAL = "CRITICAL"


class HealthCheckRequest(BaseModel):
    """Inbound request payload."""

    model_config = ConfigDict(extra="forbid")
    password_count: int = Field(ge=0, le=10_000)
    oldest_password_age_months: int = Field(ge=0, le=600)


class Recommendation(BaseModel):
    """A single actionable fix."""

    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)


class AgentScoreResponse(BaseModel):
    """Outbound response payload."""

    model_config = ConfigDict(extra="forbid")
    score: int = Field(ge=0, le=100)
    band: Band
    recommendations: list[Recommendation] = Field(max_length=5)
    message: str = Field(min_length=1, max_length=400)


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
# Recommendation catalogue (research §R6)
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
# Encouraging-tone agent prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a warm, concise coach who helps people feel good
about looking after their passwords. You never scold or use harsh words.
You keep your tone encouraging in every band — including when the score is
low — and frame each issue as a small next step the person can take.

You will be given a numeric score (0..100), a band (HEALTHY, OKAY, or
CRITICAL), the user's reported password count and oldest-password age in
months, and a short list of selected recommendations (already filtered and
ranked).

Return ONLY structured JSON matching the response schema. The score, band,
and recommendations you receive are authoritative — copy them verbatim into
your response. Your job is to write the ``message`` field: 1–3 sentences,
second person, encouraging, acknowledging the score and pointing to the
first recommendation as a friendly next step. Never invent new
recommendations. Never include URLs, code, or technical jargon.
"""


def build_user_prompt(
    *,
    password_count: int,
    oldest_password_age_months: int,
    score: int,
    band: Band,
    recommendations: list[Recommendation],
) -> str:
    """Format the user-side prompt that primes the JSON response."""
    rec_lines = (
        "\n".join(f"  - {r.id}: {r.title}" for r in recommendations) or "  - (none)"
    )
    return (
        f"password_count: {password_count}\n"
        f"oldest_password_age_months: {oldest_password_age_months}\n"
        f"score: {score}\n"
        f"band: {band.value}\n"
        f"recommendations:\n{rec_lines}\n"
    )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

logger = logging.getLogger("agent.score")

_AGENT_MODEL = "gpt-4o-mini"
_AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "15"))

app = FastAPI(title="Password Manager Health Agent", version="0.1.0")

_allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin] if _allowed_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


async def _run_llm_message(
    *,
    password_count: int,
    oldest_password_age_months: int,
    score: int,
    band: Band,
    recommendations: list[Recommendation],
) -> AgentScoreResponse:
    """Invoke the OpenAI SDK with structured output and return a typed response.

    Uses ``client.beta.chat.completions.parse`` with the Pydantic response
    model — that's the SDK's native path for guaranteed structured JSON
    (Constitution VII), and it's significantly lighter than the full
    Agents SDK so the Vercel function fits inside the 250 MB cap.
    """
    from openai import AsyncOpenAI  # local import; SDK is heavy

    client = AsyncOpenAI()
    user_prompt = build_user_prompt(
        password_count=password_count,
        oldest_password_age_months=oldest_password_age_months,
        score=score,
        band=band,
        recommendations=recommendations,
    )

    completion = await client.beta.chat.completions.parse(
        model=_AGENT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format=AgentScoreResponse,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("LLM returned no parsed structured output")
    return parsed


@app.post("/")
async def post_score(request: Request) -> Any:
    """Handle the POST request. Vercel mounts this app at ``/api/score``."""
    try:
        raw = await request.json()
    except Exception:
        return error_response(INVALID_INPUT, status=400)

    try:
        payload = HealthCheckRequest.model_validate(raw)
    except ValidationError:
        return error_response(INVALID_INPUT, status=400)

    score, band = compute_score(payload.password_count, payload.oldest_password_age_months)
    recommendations = pick_recommendations(
        payload.password_count,
        payload.oldest_password_age_months,
        score,
        band,
    )

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY missing")
        return error_response(INTERNAL_ERROR, status=500)

    try:
        llm_result = await asyncio.wait_for(
            _run_llm_message(
                password_count=payload.password_count,
                oldest_password_age_months=payload.oldest_password_age_months,
                score=score,
                band=band,
                recommendations=recommendations,
            ),
            timeout=_AGENT_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        return error_response(AGENT_TIMEOUT, status=504)
    except ValidationError:
        return error_response(AGENT_FORMAT_ERROR, status=502)
    except Exception:
        logger.exception("agent invocation failed")
        return error_response(INTERNAL_ERROR, status=500)

    safe = AgentScoreResponse(
        score=score,
        band=band,
        recommendations=recommendations,
        message=llm_result.message,
    )
    return safe.model_dump(mode="json")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_request, _exc) -> JSONResponse:
    """Catch-all that maps stray exceptions to the friendly envelope."""
    return error_response(INTERNAL_ERROR, status=500)
