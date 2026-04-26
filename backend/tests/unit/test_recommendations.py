"""Unit tests for the recommendation ranker (T023)."""

from __future__ import annotations

from agent.recommendations import pick_recommendations
from agent.schemas import Band

_FORBIDDEN_WORDS = ("stupid", "fail", "danger", "hacked", "shame", "idiot")


def _all_titles(items) -> list[str]:
    """Lowercased titles, for substring scans."""
    return [r.title.lower() for r in items]


def test_at_most_five_items() -> None:
    """The ranker MUST cap the list at five recommendations."""
    items = pick_recommendations(200, 60, 40, Band.CRITICAL)
    assert len(items) <= 5


def test_items_are_sorted_by_impact() -> None:
    """Returned items must come out in descending impact order."""
    items = pick_recommendations(60, 30, 60, Band.OKAY)
    titles = [r.title for r in items]
    # Highest-impact entry "ROTATE_OLDEST_PASSWORD" (weight 100) comes first
    # whenever applies_when matches (months >= 12).
    assert titles[0].startswith("Replace your oldest password")


def test_no_forbidden_words_in_any_title() -> None:
    """Tone gate (Constitution IV + spec SC-003) — catalogue copy stays kind."""
    items = pick_recommendations(50, 24, 70, Band.OKAY)
    for title in _all_titles(items):
        for word in _FORBIDDEN_WORDS:
            assert word not in title, f"forbidden word in recommendation: {title}"


def test_celebrate_path_for_healthy_user() -> None:
    """A user in the green band should see the celebratory recommendation."""
    items = pick_recommendations(5, 0, 100, Band.HEALTHY)
    ids = {r.id for r in items}
    assert "CELEBRATE_HEALTHY" in ids


def test_zero_passwords_offers_friendly_starter() -> None:
    """A user reporting 0 passwords gets a warm starting nudge."""
    items = pick_recommendations(0, 0, 100, Band.HEALTHY)
    ids = {r.id for r in items}
    assert "START_FIRST_PASSWORD" in ids
