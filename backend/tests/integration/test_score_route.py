"""Integration test for ``POST /agent/score`` (T024).

The OpenAI Agents SDK is mocked at the module level so this test runs
without a real API key. We assert:

  * 200 + JSON conforming to ``agent-score.schema.json`` for valid input.
  * Friendly error envelope for invalid input.
  * Friendly error envelope when the upstream times out.
"""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from agent.main import app
from agent.schemas import AgentScoreResponse, Band, Recommendation


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure the route's OPENAI_API_KEY check passes inside the test process."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")


@pytest.fixture
def client() -> TestClient:
    """A FastAPI test client bound to the real app instance."""
    return TestClient(app)


async def _fake_llm(*_args, **_kwargs) -> AgentScoreResponse:
    """Return a deterministic fake response that the route will overwrite."""
    return AgentScoreResponse(
        score=0,  # will be replaced by the route's deterministic score
        band=Band.HEALTHY,  # will be replaced
        recommendations=[],  # will be replaced
        message="Nice work — let's pick one small step today.",
    )


async def _fake_llm_timeout(*_args, **_kwargs) -> AgentScoreResponse:
    """Simulate an upstream hang that exceeds the 5 s timeout."""
    await asyncio.sleep(10)
    raise AssertionError("should have timed out")


def test_post_score_happy_path(client: TestClient) -> None:
    """Valid input returns a structured JSON body matching the contract."""
    with patch("agent.routes.score._run_llm_message", side_effect=_fake_llm):
        response = client.post(
            "/agent/score",
            json={"password_count": 12, "oldest_password_age_months": 18},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"score", "band", "recommendations", "message"}
    assert 0 <= body["score"] <= 100
    assert body["band"] in {"HEALTHY", "OKAY", "CRITICAL"}
    assert len(body["recommendations"]) <= 5
    for r in body["recommendations"]:
        assert set(r.keys()) == {"id", "title"}


def test_post_score_invalid_input_returns_friendly_envelope(client: TestClient) -> None:
    """Garbage input never reaches the LLM — the envelope is friendly."""
    response = client.post(
        "/agent/score",
        json={"password_count": -3, "oldest_password_age_months": "lots"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body == {
        "code": "INVALID_INPUT",
        "message": "I didn't quite catch that — could you give me a number?",
    }


def test_post_score_timeout_returns_friendly_envelope(client: TestClient) -> None:
    """A slow upstream is mapped to the AGENT_TIMEOUT envelope, not a stack trace."""
    with patch("agent.routes.score._run_llm_message", side_effect=_fake_llm_timeout):
        response = client.post(
            "/agent/score",
            json={"password_count": 12, "oldest_password_age_months": 18},
        )
    assert response.status_code == 504
    body = response.json()
    assert body["code"] == "AGENT_TIMEOUT"
    assert "longer than expected" in body["message"]
