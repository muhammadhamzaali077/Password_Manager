"""``POST /agent/score`` — the only route the FastAPI agent exposes.

Behaviour (research §R4 + §R5 + §R6):
  1. Validate the inbound body via :class:`HealthCheckRequest`.
  2. Compute score and band deterministically in code.
  3. Pick recommendations from the static catalogue.
  4. Ask the LLM (gpt-4o-mini, via the OpenAI Agents SDK) to produce a
     structured JSON response constrained to :class:`AgentScoreResponse`.
  5. Overwrite the score/band/recommendations fields with our deterministic
     values (defence in depth — the LLM cannot drift them).
  6. Return the validated, structured JSON. On any failure, return a
     friendly error envelope.
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, Request
from pydantic import ValidationError

from ..errors import (
    AGENT_FORMAT_ERROR,
    AGENT_TIMEOUT,
    INTERNAL_ERROR,
    INVALID_INPUT,
    error_response,
)
from ..prompts import SYSTEM_PROMPT, build_user_prompt
from ..recommendations import pick_recommendations
from ..schemas import AgentScoreResponse, Band, HealthCheckRequest, Recommendation
from ..scoring import compute_score

router = APIRouter()
logger = logging.getLogger("agent.score")

_AGENT_MODEL = "gpt-4o-mini"
_AGENT_TIMEOUT_SECONDS = 15.0


async def _run_llm_message(
    *,
    password_count: int,
    oldest_password_age_months: int,
    score: int,
    band: Band,
    recommendations: list[Recommendation],
) -> AgentScoreResponse:
    """Invoke the OpenAI Agents SDK and parse a structured response.

    Imports are local so that unit tests can run without the SDK installed
    and so that startup of the FastAPI app is unaffected by SDK init costs.
    """
    from agents import Agent, Runner  # type: ignore  # local import; SDK is heavy

    rec_dicts = [{"id": r.id, "title": r.title} for r in recommendations]
    user_prompt = build_user_prompt(
        password_count=password_count,
        oldest_password_age_months=oldest_password_age_months,
        score=score,
        band=band,
        recommendations=rec_dicts,
    )
    agent = Agent(
        name="PasswordHealthCoach",
        instructions=SYSTEM_PROMPT,
        model=_AGENT_MODEL,
        output_type=AgentScoreResponse,
    )
    result = await Runner.run(agent, input=user_prompt)
    return result.final_output


@router.post("/score")
async def post_score(request: Request):
    """Handle ``POST /agent/score`` — the structured-JSON entry point.

    Args:
        request: The incoming FastAPI request. The body MUST conform to
            :class:`HealthCheckRequest`.

    Returns:
        A structured :class:`AgentScoreResponse` body on success, or a
        friendly error envelope (:func:`error_response`) on failure.
    """
    raw = await request.json()
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

    # Defence in depth: the deterministic values always win.
    safe = AgentScoreResponse(
        score=score,
        band=band,
        recommendations=recommendations,
        message=llm_result.message,
    )
    return safe.model_dump(mode="json")
