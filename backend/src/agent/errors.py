"""Error envelope helpers for the password-health agent.

Constitution IV requires user-facing errors to be friendly. Every non-2xx
response from this service follows ``{ "code": <STABLE_UPPER_SNAKE>,
"message": <user_safe_text> }`` (Constitution VII). Internal exception
messages, stack traces, and framework jargon never leak through here.
"""

from __future__ import annotations

from typing import Final

from fastapi.responses import JSONResponse

# Reserved, stable error codes shared across the whole product.
INVALID_INPUT: Final[str] = "INVALID_INPUT"
AGENT_TIMEOUT: Final[str] = "AGENT_TIMEOUT"
AGENT_FORMAT_ERROR: Final[str] = "AGENT_FORMAT_ERROR"
RATE_LIMITED: Final[str] = "RATE_LIMITED"
INTERNAL_ERROR: Final[str] = "INTERNAL_ERROR"

# Default user-safe wording per code. Friendly, second-person, never alarmist.
_DEFAULT_MESSAGES: Final[dict[str, str]] = {
    INVALID_INPUT: "I didn't quite catch that — could you give me a number?",
    AGENT_TIMEOUT: "That took longer than expected. Want to try once more?",
    AGENT_FORMAT_ERROR: "I had trouble putting that together. Mind sending it again?",
    RATE_LIMITED: "You're moving fast! Give it a moment and try again.",
    INTERNAL_ERROR: "Something hiccuped on our side. Please try again in a bit.",
}


def friendly_message_for(code: str) -> str:
    """Return the default user-safe message for a stable error code.

    Args:
        code: One of the reserved upper-snake codes defined in this module.

    Returns:
        A short, encouraging sentence safe to render directly to the user.
    """
    return _DEFAULT_MESSAGES.get(code, _DEFAULT_MESSAGES[INTERNAL_ERROR])


def error_response(code: str, status: int, message: str | None = None) -> JSONResponse:
    """Build a JSONResponse following the error-envelope contract.

    Args:
        code: One of the reserved error codes.
        status: HTTP status code to return (4xx for client errors, 5xx otherwise).
        message: Optional override for the user-facing text. If omitted, the
            default friendly message for ``code`` is used.

    Returns:
        A FastAPI ``JSONResponse`` whose body is exactly
        ``{"code": code, "message": message}``.
    """
    return JSONResponse(
        status_code=status,
        content={"code": code, "message": message or friendly_message_for(code)},
    )
