"""Petals bridge loopback shim route (CF-335 P0).

OpenAI-compatible ``POST /chat/completions`` under ``settings.petals_bridge_base_path``
(default ``/api/petals/v1``). This is the data-plane endpoint the Pi engine's
identity-pinned ``pi-petals-<node>`` catalog entries point at. Fail-closed: any
:class:`PetalsUnavailable` becomes HTTP 503 with ``error.type=petals_unavailable`` —
never a fallback to a paid route.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.petals_bridge import PetalsUnavailable, chat_completions

router = APIRouter()


@router.post("/chat/completions")
async def petals_chat_completions(payload: dict) -> JSONResponse:
    if not settings.petals_bridge_enabled:
        return JSONResponse(
            status_code=503,
            content={"error": {"type": "petals_unavailable", "reason": "bridge_disabled"}},
        )
    try:
        result = await chat_completions(payload)
    except PetalsUnavailable as exc:
        return JSONResponse(
            status_code=503,
            content={"error": {"type": "petals_unavailable", "reason": exc.reason}},
        )
    return JSONResponse(status_code=200, content=result)
