"""FastAPI application entrypoint for the password-health agent.

Loads environment variables, configures CORS for the Next.js front end, and
mounts the single ``POST /agent/score`` route. All non-2xx responses follow
the friendly error envelope defined in :mod:`agent.errors` (Constitution IV).
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .errors import INTERNAL_ERROR, error_response
from .routes.score import router as score_router

load_dotenv()

app = FastAPI(title="Password Manager Health Agent", version="0.1.0")

_allowed_origin = os.getenv("ALLOWED_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(score_router, prefix="/agent")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    """Liveness probe — returns ``{"status": "ok"}``.

    Returns:
        A small JSON object. Not part of the user-facing contract; used by
        local dev and the Vercel platform.
    """
    return {"status": "ok"}


@app.exception_handler(Exception)
async def _unhandled_exception_handler(_request, _exc):
    """Catch-all that maps stray exceptions to the friendly envelope.

    Args:
        _request: Unused; required by the FastAPI handler signature.
        _exc: The unhandled exception. We never echo its content to users.

    Returns:
        A friendly :class:`fastapi.responses.JSONResponse` with status 500.
    """
    return error_response(INTERNAL_ERROR, status=500)
