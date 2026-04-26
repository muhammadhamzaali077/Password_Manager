"""Deterministic password-health score computation.

The score and band are computed in code (never by the LLM) so that the same
inputs always yield the same output — a precondition for the user being able
to track real progress across sessions (spec FR-003 + Assumptions).
"""

from __future__ import annotations

from .schemas import Band

# Spec thresholds (see spec.md Assumptions and research.md §R5).
_HEALTHY_FLOOR = 80
_OKAY_FLOOR = 50

# Tunable coefficients.
_AGE_WEIGHT = 0.50          # months above zero pull the score down fastest
_COUNT_OVERAGE_WEIGHT = 0.20  # extra password count above the comfort threshold
_COUNT_COMFORT_THRESHOLD = 50


def _clamp(value: float, lo: int, hi: int) -> int:
    """Clamp a number into the closed integer range ``[lo, hi]``."""
    return max(lo, min(hi, int(round(value))))


def band_for(score: int) -> Band:
    """Return the band a numeric score belongs to.

    Args:
        score: An integer in ``[0, 100]``.

    Returns:
        The matching :class:`Band` per spec thresholds.
    """
    if score >= _HEALTHY_FLOOR:
        return Band.HEALTHY
    if score >= _OKAY_FLOOR:
        return Band.OKAY
    return Band.CRITICAL


def compute_score(password_count: int, oldest_password_age_months: int) -> tuple[int, Band]:
    """Compute the password-health score from the two user-provided inputs.

    Args:
        password_count: Number of passwords managed by the user (0..10000).
        oldest_password_age_months: Age in months of the oldest password (0..600).

    Returns:
        A ``(score, band)`` tuple. ``score`` is an integer in ``[0, 100]`` and
        ``band`` is the corresponding :class:`Band`.
    """
    count_overage = max(0, password_count - _COUNT_COMFORT_THRESHOLD)
    raw = (
        100
        - _COUNT_OVERAGE_WEIGHT * count_overage
        - _AGE_WEIGHT * oldest_password_age_months
    )
    score = _clamp(raw, 0, 100)
    return score, band_for(score)
