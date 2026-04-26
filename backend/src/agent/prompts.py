"""System and user prompts for the password-health agent.

Tone is enforced here in one place (FR-009 + Constitution IV). The agent's
*only* creative contribution is the ``message`` field — the score, band, and
recommendations are computed deterministically and overwrite anything the
model returns for those fields.
"""

from __future__ import annotations

from .schemas import Band

SYSTEM_PROMPT = """You are a warm, concise coach who helps people feel good
about looking after their passwords. You never scold, never use words like
"fail", "danger", "hacked", "stupid", or "shame". You keep your tone
encouraging in every band — including when the score is low — and frame each
issue as a small next step the person can take.

You will be given:
  - a numeric score (0..100)
  - a band (HEALTHY, OKAY, or CRITICAL)
  - the user's reported password count and oldest-password age in months
  - a short list of selected recommendations (already filtered and ranked)

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
    recommendations: list[dict[str, str]],
) -> str:
    """Format the user-side prompt that primes the JSON response.

    Args:
        password_count: User-reported number of passwords.
        oldest_password_age_months: User-reported age of the oldest password.
        score: Pre-computed deterministic score.
        band: Pre-computed band.
        recommendations: Pre-selected recommendations as ``{id, title}`` dicts.

    Returns:
        A plain-text prompt string suitable to send as the user message.
    """
    rec_lines = "\n".join(f"  - {r['id']}: {r['title']}" for r in recommendations) or "  - (none)"
    return (
        f"password_count: {password_count}\n"
        f"oldest_password_age_months: {oldest_password_age_months}\n"
        f"score: {score}\n"
        f"band: {band.value}\n"
        f"recommendations:\n{rec_lines}\n"
    )
