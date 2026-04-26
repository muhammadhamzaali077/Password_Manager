"""Unit tests for the deterministic scoring formula (T022)."""

from __future__ import annotations

import pytest

from agent.schemas import Band
from agent.scoring import band_for, compute_score


@pytest.mark.parametrize(
    ("count", "months", "expected_score", "expected_band"),
    [
        # Pristine inputs — top of the green band.
        (0, 0, 100, Band.HEALTHY),
        (10, 0, 100, Band.HEALTHY),
        # Brand-new oldest password keeps you in the green even at 50 entries.
        (50, 0, 100, Band.HEALTHY),
        # 12 months of age pulls 6 points off → still HEALTHY.
        (12, 12, 94, Band.HEALTHY),
        # 30 months of age + 60 entries pulls a noticeable amount → still HEALTHY at the edge.
        (60, 30, 83, Band.HEALTHY),
        # Mid-range: yellow band.
        (40, 60, 70, Band.OKAY),
        (10, 80, 60, Band.OKAY),
        # Critical band.
        (200, 60, 40, Band.CRITICAL),
        (5, 120, 40, Band.CRITICAL),
        # Floor.
        (10000, 600, 0, Band.CRITICAL),
    ],
)
def test_compute_score_table(
    count: int, months: int, expected_score: int, expected_band: Band
) -> None:
    """Table-driven assertion that the formula is deterministic and bounded."""
    score, band = compute_score(count, months)
    assert (score, band) == (expected_score, expected_band)


def test_band_thresholds() -> None:
    """Boundary values fall into the band defined by spec Assumptions."""
    assert band_for(80) is Band.HEALTHY
    assert band_for(79) is Band.OKAY
    assert band_for(50) is Band.OKAY
    assert band_for(49) is Band.CRITICAL
    assert band_for(0) is Band.CRITICAL
    assert band_for(100) is Band.HEALTHY


def test_score_is_clamped_to_range() -> None:
    """No matter how extreme the input, the result is always in [0, 100]."""
    score_low, _ = compute_score(10000, 600)
    score_high, _ = compute_score(0, 0)
    assert 0 <= score_low <= 100
    assert 0 <= score_high <= 100


def test_compute_score_is_deterministic() -> None:
    """Same input → same output, every time (spec Assumption: deterministic)."""
    a = compute_score(12, 18)
    b = compute_score(12, 18)
    assert a == b
