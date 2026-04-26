"""Tone-review test (T045) — Constitution IV + spec SC-003.

Asserts that the system prompt and every line of catalogue copy stays
encouraging: no alarmist, shaming, or scary words leak in.
"""

from __future__ import annotations

import re

from agent.errors import _DEFAULT_MESSAGES
from agent.prompts import SYSTEM_PROMPT
from agent.recommendations import _CATALOGUE

_FORBIDDEN = re.compile(
    r"\b(stupid|fail|danger|hacked|shame|idiot|terrible|awful|disaster)\b",
    re.IGNORECASE,
)


def test_system_prompt_avoids_alarmist_words() -> None:
    """The system prompt must not contain forbidden words.

    Note: the prompt is allowed to *forbid* the words in instructions to the
    model, so we strip the explicit allow-list line before checking.
    """
    sanitized = re.sub(
        r'"fail",\s*"danger",\s*"hacked",\s*"stupid",\s*or\s*"shame"',
        "",
        SYSTEM_PROMPT,
    )
    assert _FORBIDDEN.search(sanitized) is None


def test_catalogue_titles_avoid_alarmist_words() -> None:
    """Every catalogue entry must read encouragingly."""
    for entry in _CATALOGUE:
        assert _FORBIDDEN.search(entry.title) is None, entry.id


def test_friendly_messages_avoid_alarmist_words() -> None:
    """Default error messages must stay friendly."""
    for code, message in _DEFAULT_MESSAGES.items():
        assert _FORBIDDEN.search(message) is None, code
