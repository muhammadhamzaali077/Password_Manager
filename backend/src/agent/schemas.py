"""Pydantic models that mirror ``contracts/agent-score.schema.json``.

These models are the Constitution-VII contract on the Python side: every
request body and every response body for the FastAPI agent passes through
one of them. The contract test in ``tests/contract/`` keeps this module and
the JSON schema in lock-step.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Band(str, Enum):
    """Score band used for color coding the result card."""

    HEALTHY = "HEALTHY"
    OKAY = "OKAY"
    CRITICAL = "CRITICAL"


class HealthCheckRequest(BaseModel):
    """Inbound request payload for ``POST /agent/score``.

    Attributes:
        password_count: Number of passwords the user currently manages.
        oldest_password_age_months: Age (in months) of the oldest password.
    """

    model_config = ConfigDict(extra="forbid")

    password_count: int = Field(ge=0, le=10_000)
    oldest_password_age_months: int = Field(ge=0, le=600)


class Recommendation(BaseModel):
    """A single actionable fix shown beneath the score card.

    Attributes:
        id: Stable upper-snake catalogue identifier.
        title: Short, encouraging, user-facing fix description.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=120)


class AgentScoreResponse(BaseModel):
    """Outbound response payload for ``POST /agent/score``.

    Attributes:
        score: Computed health score, 0..100 inclusive.
        band: Band derived from ``score`` per spec thresholds.
        recommendations: At most five fixes, ordered by impact (descending).
        message: Encouraging wrapper text the chat shows above the card.
    """

    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    band: Band
    recommendations: list[Recommendation] = Field(max_length=5)
    message: str = Field(min_length=1, max_length=400)
