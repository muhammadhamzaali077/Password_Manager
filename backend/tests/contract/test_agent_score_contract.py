"""Contract test — keeps :class:`AgentScoreResponse` and the JSON schema in sync.

Constitution VII forbids the FastAPI agent from drifting away from a stable
JSON contract. This test loads ``contracts/agent-score.schema.json`` and
asserts that the Pydantic-generated schema for ``AgentScoreResponse``
contains every field described by the JSON schema's ``Response`` definition,
with matching constraints.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.schemas import AgentScoreResponse, HealthCheckRequest

CONTRACT_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "agent"
    / "contracts"
    / "agent-score.schema.json"
)


@pytest.fixture(scope="module")
def contract() -> dict:
    """Load the canonical JSON Schema for the agent contract."""
    with CONTRACT_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def test_response_schema_required_fields(contract: dict) -> None:
    """Every required field in the JSON schema must exist on the Pydantic model."""
    required = contract["definitions"]["Response"]["required"]
    pydantic_fields = set(AgentScoreResponse.model_fields.keys())
    for field in required:
        assert field in pydantic_fields, f"missing field on AgentScoreResponse: {field}"


def test_request_schema_required_fields(contract: dict) -> None:
    """Every required field in the request schema must exist on HealthCheckRequest."""
    required = contract["definitions"]["Request"]["required"]
    pydantic_fields = set(HealthCheckRequest.model_fields.keys())
    for field in required:
        assert field in pydantic_fields, f"missing field on HealthCheckRequest: {field}"


def test_recommendation_max_items(contract: dict) -> None:
    """The recommendations list must be capped at five items per the contract."""
    rec_field = AgentScoreResponse.model_fields["recommendations"]
    assert rec_field.metadata is not None
    max_length = next(
        (m.max_length for m in rec_field.metadata if hasattr(m, "max_length")),
        None,
    )
    assert max_length == contract["definitions"]["Response"]["properties"]["recommendations"][
        "maxItems"
    ]


def test_band_enum_matches(contract: dict) -> None:
    """Band enum values in the model must equal the JSON schema enum values."""
    from agent.schemas import Band

    contract_values = set(contract["definitions"]["Band"]["enum"])
    model_values = {b.value for b in Band}
    assert model_values == contract_values
