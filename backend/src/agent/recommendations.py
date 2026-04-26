"""Static catalogue of fixes plus the deterministic ranker.

The catalogue is small and human-tuned. Each entry carries an ``impact_weight``
(higher = more impactful) and an ``applies_when`` predicate evaluated against
the inputs and the computed score. We always return at most five entries,
sorted by ``impact_weight`` descending — never asking the LLM to invent
recommendations (research §R6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .schemas import Band, Recommendation

Predicate = Callable[[int, int, int, Band], bool]


@dataclass(frozen=True)
class _CatalogueEntry:
    """A single recommendation candidate in the catalogue."""

    id: str
    title: str
    impact_weight: int
    applies_when: Predicate


def _always(_count: int, _months: int, _score: int, _band: Band) -> bool:
    """Predicate that matches every (inputs, score)."""
    return True


_CATALOGUE: tuple[_CatalogueEntry, ...] = (
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
    _CatalogueEntry(
        # Narrow predicate (no passwords yet) — when it fires it should lead.
        id="START_FIRST_PASSWORD",
        title="Save your first password to the manager — you've got a great place to start.",
        impact_weight=110,
        applies_when=lambda c, m, s, b: c == 0,
    ),
    _CatalogueEntry(
        # Narrow predicate (HEALTHY band) — surface near the top when applicable.
        id="CELEBRATE_HEALTHY",
        title="Keep up the routine — a quick monthly check keeps you in the green.",
        impact_weight=105,
        applies_when=lambda c, m, s, b: b is Band.HEALTHY,
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
    """Select the top recommendations for a given check.

    Args:
        password_count: User-reported number of passwords.
        oldest_password_age_months: User-reported age of the oldest password.
        score: Computed score.
        band: Computed band.
        limit: Maximum number of recommendations to return (defaults to 5).

    Returns:
        A list of :class:`Recommendation` of length at most ``limit``,
        ordered by impact descending. Items whose ``applies_when`` predicate
        is false for the inputs are filtered out before ranking.
    """
    matched = [
        e
        for e in _CATALOGUE
        if e.applies_when(password_count, oldest_password_age_months, score, band)
    ]
    matched.sort(key=lambda e: e.impact_weight, reverse=True)
    return [Recommendation(id=e.id, title=e.title) for e in matched[:limit]]
