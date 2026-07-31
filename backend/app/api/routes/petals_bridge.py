"""Petals bridge loopback shim route (CF-335 P0 / CF-336 P1).

OpenAI-compatible endpoints under ``settings.petals_bridge_base_path``
(default ``/api/petals/v1``). Data plane for the Pi engine's identity-pinned
``pi-petals-<node>`` catalog entries. Fail-closed everywhere: any
:class:`PetalsUnavailable` becomes HTTP 503 with ``error.type=petals_unavailable``
— never a fallback to a paid route.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.config import settings
from app.core.permissions import require_global_role
from app.core.petals_bridge import (
    PetalsUnavailable,
    bridge_status,
    chat_completions,
    chat_completions_stream,
    set_donor_consent,
)

router = APIRouter()


def _unavailable(exc: PetalsUnavailable) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={"error": {"type": "petals_unavailable", "reason": exc.reason}},
    )


@router.post("/chat/completions", response_model=None)
async def petals_chat_completions(payload: dict):
    if not settings.petals_bridge_enabled:
        return JSONResponse(
            status_code=503,
            content={"error": {"type": "petals_unavailable", "reason": "bridge_disabled"}},
        )
    if payload.get("stream"):
        async def sse():
            try:
                async for chunk in chat_completions_stream(payload):
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            except PetalsUnavailable as exc:
                yield f"data: {json.dumps({'error': {'type': 'petals_unavailable', 'reason': exc.reason}})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(sse(), media_type="text/event-stream")
    try:
        result = await chat_completions(payload)
    except PetalsUnavailable as exc:
        return _unavailable(exc)
    return JSONResponse(status_code=200, content=result)


@router.get("/status")
async def petals_status(request: Request) -> dict:
    """Bridge-visible donor inventory (admin)."""
    require_global_role(request, "admin")
    return bridge_status()


@router.post("/consent")
async def petals_consent(payload: dict, request: Request) -> JSONResponse:
    """Admin-managed donor consent flip (pi_served)."""
    require_global_role(request, "admin")
    node_id = str(payload.get("node_id") or "")
    if not node_id:
        return JSONResponse(status_code=422, content={"error": {"type": "validation", "reason": "node_id_required"}})
    try:
        state = set_donor_consent(node_id, bool(payload.get("pi_served", False)))
    except PetalsUnavailable as exc:
        return _unavailable(exc)
    return JSONResponse(status_code=200, content=state)
