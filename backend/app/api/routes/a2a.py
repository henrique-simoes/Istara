"""A2A discovery and JSON-RPC routes."""

from __future__ import annotations

import hashlib
import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from app.config import settings as app_settings
from app.core.client_identity import BoundedWindowRateLimiter, get_client_ip
from app.core.permissions import require_project_access
from app.core.pi_replacement import record_pi_a2a_event
from app.core.replay_cache import BoundedReplayCache
from app.core.version import read_istara_version
from app.models.database import async_session

router = APIRouter()

ISTARA_VERSION = read_istara_version()
A2A_MAX_BODY_BYTES = 64 * 1024
A2A_MAX_CONTENT_CHARS = 16_000
A2A_MAX_METADATA_BYTES = 16 * 1024
A2A_MAX_AGENT_ID_CHARS = 120
_a2a_rate_limiter = BoundedWindowRateLimiter(max_clients=4096)
_a2a_tasks_send_rate_limiter = BoundedWindowRateLimiter(max_clients=4096)
_a2a_replay_cache = BoundedReplayCache(max_entries=8192)


def _a2a_jsonrpc_error(
    status_code: int,
    code: int,
    message: str,
    req_id=None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "jsonrpc": "2.0",
            "error": {"code": code, "message": message},
            "id": req_id,
        },
    )


async def _record_a2a_event(
    request: Request,
    event_type: str,
    *,
    user_id: str = "",
    status_code: int = 200,
    details: dict | None = None,
) -> None:
    try:
        from app.core.auth_audit import record_auth_event

        await record_auth_event(
            request,
            event_type,
            user_id=user_id,
            status_code=status_code,
            details=details or {},
        )
    except Exception:
        pass


def _a2a_client_key(request: Request, user_context: dict) -> str:
    user_id = str(user_context.get("id") or "anonymous")
    client_ip = get_client_ip(request, app_settings.trusted_proxy_hosts)
    return f"{user_id}:{client_ip}"


async def _authorize_agent_card_request(request: Request) -> dict | JSONResponse:
    """Authorize team-mode agent-card disclosure without JSON-RPC envelopes."""
    from app.core.auth import verify_token
    from app.core.auth_cookies import get_auth_cookie_token
    from app.core.auth_sessions import current_user_context_for_payload, validate_auth_session
    from app.core.permissions import global_role_rank
    from app.core.security_middleware import browser_origin_denial

    origin_denial = browser_origin_denial(request, require_cookie_auth=True)
    if origin_denial:
        await _record_a2a_event(
            request,
            "a2a.agent_card.denied",
            status_code=403,
            details={"reason": "origin_denied"},
        )
        return JSONResponse(status_code=403, content={"detail": origin_denial})

    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        token = get_auth_cookie_token(request)
    if not token:
        await _record_a2a_event(
            request,
            "a2a.agent_card.denied",
            status_code=401,
            details={"reason": "missing_auth"},
        )
        return JSONResponse(status_code=401, content={"detail": "Authentication required."})

    payload = verify_token(token)
    if not payload:
        await _record_a2a_event(
            request,
            "a2a.agent_card.denied",
            status_code=401,
            details={"reason": "invalid_token"},
        )
        return JSONResponse(status_code=401, content={"detail": "Invalid or expired token."})

    async with async_session() as db:
        if not await validate_auth_session(db, payload, request):
            await _record_a2a_event(
                request,
                "a2a.agent_card.denied",
                user_id=str(payload.get("sub", "")),
                status_code=401,
                details={"reason": "revoked_session"},
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or revoked authentication session."},
            )
        user_context = await current_user_context_for_payload(db, payload)
        if not user_context:
            await _record_a2a_event(
                request,
                "a2a.agent_card.denied",
                user_id=str(payload.get("sub", "")),
                status_code=401,
                details={"reason": "missing_user"},
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Authenticated user no longer exists."},
            )

    if global_role_rank(user_context.get("role")) < global_role_rank("researcher"):
        await _record_a2a_event(
            request,
            "a2a.agent_card.denied",
            user_id=str(user_context.get("id", "")),
            status_code=403,
            details={"reason": "insufficient_role"},
        )
        return JSONResponse(status_code=403, content={"detail": "Researcher access required."})

    await _record_a2a_event(
        request,
        "a2a.agent_card.allowed",
        user_id=str(user_context.get("id", "")),
        status_code=200,
    )
    return user_context


async def _authorize_a2a_request(request: Request) -> dict | JSONResponse:
    """Authorize JSON-RPC A2A access using Istara's normal auth contracts."""
    if not app_settings.team_mode:
        from app.core.network_security import (
            _extract_token,
            _is_localhost,
            remote_local_admin_block_reason,
        )

        client_host = request.client.host if request.client else None
        denial = remote_local_admin_block_reason(client_host, request.url.path)
        if denial:
            return _a2a_jsonrpc_error(403, -32003, denial)
        if app_settings.network_access_token and not _is_localhost(client_host):
            token = _extract_token(request)
            if token != app_settings.network_access_token:
                return _a2a_jsonrpc_error(
                    401,
                    -32000,
                    "Network access token required for A2A JSON-RPC access.",
                )
        return {"id": "local", "username": "local", "role": "admin"}

    from app.core.auth import verify_token
    from app.core.auth_cookies import get_auth_cookie_token
    from app.core.auth_sessions import current_user_context_for_payload, validate_auth_session
    from app.core.permissions import global_role_rank
    from app.core.security_middleware import browser_origin_denial

    origin_denial = browser_origin_denial(request, require_cookie_auth=True)
    if origin_denial:
        return _a2a_jsonrpc_error(403, -32003, origin_denial)

    auth_header = request.headers.get("authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    if not token:
        token = get_auth_cookie_token(request)
    if not token:
        return _a2a_jsonrpc_error(401, -32000, "Authentication required for A2A JSON-RPC.")

    payload = verify_token(token)
    if not payload:
        return _a2a_jsonrpc_error(401, -32000, "Invalid or expired authentication token.")

    async with async_session() as db:
        if not await validate_auth_session(db, payload, request):
            return _a2a_jsonrpc_error(401, -32000, "Invalid or revoked authentication session.")
        user_context = await current_user_context_for_payload(db, payload)
        if not user_context:
            return _a2a_jsonrpc_error(401, -32000, "Authenticated user no longer exists.")

    if global_role_rank(user_context.get("role")) < global_role_rank("researcher"):
        return _a2a_jsonrpc_error(403, -32003, "Researcher access required for A2A JSON-RPC.")
    return user_context


def _a2a_limited_text(value: object, field_name: str, max_chars: int) -> str:
    if value is None:
        return ""
    text = str(value)
    if len(text) > max_chars:
        raise ValueError(f"{field_name} exceeds maximum length of {max_chars} characters")
    return text


def _a2a_metadata(value: object) -> dict:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("message.metadata must be a JSON object")
    encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
    if len(encoded) > A2A_MAX_METADATA_BYTES:
        raise ValueError(
            f"message.metadata exceeds maximum size of {A2A_MAX_METADATA_BYTES} bytes"
        )
    return value


def _a2a_project_id(*sources: dict) -> str | None:
    for source in sources:
        value = source.get("project_id") or source.get("projectId")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


async def _authorize_project_scope(
    db,
    request: Request,
    project_id: str,
    req_id,
    *,
    min_role: str,
) -> JSONResponse | None:
    try:
        await require_project_access(db, request, project_id, min_role=min_role)
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, str) else "Project access denied."
        return _a2a_jsonrpc_error(exc.status_code, -32043, detail, req_id)
    return None


@router.get("/.well-known/agent.json")
async def agent_card(request: Request):
    """A2A Protocol: Agent Card discovery endpoint."""
    if app_settings.team_mode and app_settings.a2a_agent_card_auth_required_team_mode:
        authorized = await _authorize_agent_card_request(request)
        if isinstance(authorized, JSONResponse):
            return authorized
    return {
        "name": "Istara",
        "description": (
            "Local-first AI agent for UX Research - analyzes interviews, surveys, "
            "usability tests and more using 40+ research skills."
        ),
        "url": "http://localhost:8000",
        "version": ISTARA_VERSION,
        "protocol_version": "0.1",
        "capabilities": {
            "streaming": False,
            "push_notifications": False,
            "state_transition_history": True,
        },
        "skills": [
            {
                "id": "ux-research",
                "name": "UX Research Analysis",
                "description": (
                    "Analyzes user interviews, surveys, usability tests, and field "
                    "studies to extract insights and recommendations."
                ),
                "tags": ["ux", "research", "analysis", "interviews", "surveys"],
                "examples": [
                    "Analyze these interview transcripts",
                    "Run thematic analysis on survey responses",
                    "Create personas from research data",
                ],
            }
        ],
        "default_input_modes": ["text/plain", "application/json"],
        "default_output_modes": ["application/json"],
    }


@router.post("/a2a")
async def a2a_jsonrpc(request: Request):
    """A2A Protocol: JSON-RPC 2.0 endpoint for agent-to-agent communication."""
    authorized = await _authorize_a2a_request(request)
    if isinstance(authorized, JSONResponse):
        await _record_a2a_event(
            request,
            "a2a.jsonrpc.denied",
            status_code=authorized.status_code,
            details={"reason": "authorization_failed"},
        )
        return authorized
    request.state.user = authorized

    client_key = _a2a_client_key(request, authorized)
    if _a2a_rate_limiter.is_limited(
        client_key,
        limit=max(1, int(app_settings.a2a_rate_limit_per_minute)),
        window_seconds=60,
    ):
        await _record_a2a_event(
            request,
            "a2a.jsonrpc.rate_limited",
            user_id=str(authorized.get("id", "")),
            status_code=429,
            details={"scope": "all_methods"},
        )
        return _a2a_jsonrpc_error(429, -32029, "A2A rate limit exceeded.")

    req_id = None
    raw_body = b""
    try:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > A2A_MAX_BODY_BYTES:
            return _a2a_jsonrpc_error(413, -32013, "A2A request body too large.", req_id)
    except ValueError:
        return _a2a_jsonrpc_error(400, -32600, "Invalid Content-Length header.", req_id)

    try:
        raw_body = await request.body()
        if len(raw_body) > A2A_MAX_BODY_BYTES:
            return _a2a_jsonrpc_error(413, -32013, "A2A request body too large.", req_id)
        body = json.loads(raw_body)
    except Exception:
        return _a2a_jsonrpc_error(400, -32700, "Parse error", req_id)

    if not isinstance(body, dict):
        return _a2a_jsonrpc_error(400, -32600, "JSON-RPC request must be an object.", req_id)

    method = body.get("method", "")
    req_id = body.get("id")
    params = body.get("params", {})
    if not isinstance(params, dict):
        return _a2a_jsonrpc_error(400, -32602, "params must be an object.", req_id)

    if method == "tasks/send":
        if req_id is None:
            await _record_a2a_event(
                request,
                "a2a.tasks_send.denied",
                user_id=str(authorized.get("id", "")),
                status_code=400,
                details={"reason": "missing_jsonrpc_id"},
            )
            return _a2a_jsonrpc_error(
                400,
                -32600,
                "JSON-RPC id is required for tasks/send replay protection.",
                req_id,
            )
        if _a2a_tasks_send_rate_limiter.is_limited(
            client_key,
            limit=max(1, int(app_settings.a2a_tasks_send_rate_limit_per_minute)),
            window_seconds=60,
        ):
            await _record_a2a_event(
                request,
                "a2a.tasks_send.rate_limited",
                user_id=str(authorized.get("id", "")),
                status_code=429,
            )
            return _a2a_jsonrpc_error(429, -32029, "A2A tasks/send rate limit exceeded.", req_id)

        body_hash = hashlib.sha256(raw_body).hexdigest()
        replay_key = hashlib.sha256(
            f"{authorized.get('id', '')}:{method}:{json.dumps(req_id, sort_keys=True, default=str)}:{body_hash}".encode(
                "utf-8"
            )
        ).hexdigest()
        if _a2a_replay_cache.seen_or_store(
            replay_key,
            ttl_seconds=max(1, int(app_settings.a2a_replay_ttl_seconds)),
        ):
            await _record_a2a_event(
                request,
                "a2a.tasks_send.replay_rejected",
                user_id=str(authorized.get("id", "")),
                status_code=409,
                details={"jsonrpc_id": str(req_id)[:120]},
            )
            return _a2a_jsonrpc_error(409, -32009, "A2A replay detected.", req_id)

        from app.services import a2a as a2a_svc

        try:
            message = params.get("message", {})
            if not isinstance(message, dict):
                raise ValueError("message must be an object")
            metadata = _a2a_metadata(message.get("metadata"))
            project_id = _a2a_project_id(metadata, params)
            if not project_id:
                return _a2a_jsonrpc_error(
                    400,
                    -32602,
                    "project_id is required for A2A tasks/send.",
                    req_id,
                )
            metadata["project_id"] = project_id
            metadata["submitted_by_user_id"] = authorized.get("id", "")
            metadata["submitted_by_username"] = authorized.get("username", "")
            from_agent_id = _a2a_limited_text(
                params.get("from", "external"), "from", A2A_MAX_AGENT_ID_CHARS
            )
            to_agent_id = _a2a_limited_text(
                params.get("to", "istara-main"), "to", A2A_MAX_AGENT_ID_CHARS
            )
            content = _a2a_limited_text(
                message.get("text", ""), "message.text", A2A_MAX_CONTENT_CHARS
            )
        except ValueError as exc:
            return _a2a_jsonrpc_error(400, -32602, str(exc), req_id)

        async with async_session() as db:
            denied = await _authorize_project_scope(
                db,
                request,
                project_id,
                req_id,
                min_role="researcher",
            )
            if denied:
                return denied
            try:
                msg = await a2a_svc.send_message(
                    db,
                    from_agent_id=from_agent_id or "external",
                    to_agent_id=to_agent_id or "istara-main",
                    message_type="a2a_task",
                    content=content,
                    project_id=project_id,
                    metadata=metadata,
                )
            except ValueError as exc:
                return _a2a_jsonrpc_error(400, -32602, str(exc), req_id)
            await _record_a2a_event(
                request,
                "a2a.tasks_send.accepted",
                user_id=str(authorized.get("id", "")),
                status_code=200,
                details={
                    "message_id": msg["id"],
                    "from_agent_id": from_agent_id or "external",
                    "to_agent_id": to_agent_id or "istara-main",
                },
            )
            await record_pi_a2a_event(
                request=request,
                project_id=project_id,
                metadata=metadata,
                message_id=msg["id"],
                from_agent_id=from_agent_id or "external",
                to_agent_id=to_agent_id or "istara-main",
            )
            return {
                "jsonrpc": "2.0",
                "result": {"id": msg["id"], "status": "submitted"},
                "id": req_id,
            }

    if method == "tasks/get":
        from app.services import a2a as a2a_svc

        task_id = params.get("id")
        project_id = _a2a_project_id(params)
        if not project_id:
            return _a2a_jsonrpc_error(
                400,
                -32602,
                "project_id is required for A2A tasks/get.",
                req_id,
            )
        async with async_session() as db:
            denied = await _authorize_project_scope(
                db,
                request,
                project_id,
                req_id,
                min_role="viewer",
            )
            if denied:
                return denied
            messages = await a2a_svc.get_full_log(db, limit=200, project_id=project_id)
            task = next((m for m in messages if m["id"] == task_id), None)
            if task:
                return {"jsonrpc": "2.0", "result": task, "id": req_id}
            return JSONResponse(
                status_code=404,
                content={
                    "jsonrpc": "2.0",
                    "error": {"code": -32001, "message": "Task not found"},
                    "id": req_id,
                },
            )

    if method == "tasks/list":
        from app.services import a2a as a2a_svc

        project_id = _a2a_project_id(params)
        if not project_id:
            return _a2a_jsonrpc_error(
                400,
                -32602,
                "project_id is required for A2A tasks/list.",
                req_id,
            )
        try:
            limit = int(params.get("limit", 50))
        except (TypeError, ValueError):
            return _a2a_jsonrpc_error(400, -32602, "limit must be an integer.", req_id)
        limit = max(1, min(limit, 200))

        async with async_session() as db:
            denied = await _authorize_project_scope(
                db,
                request,
                project_id,
                req_id,
                min_role="viewer",
            )
            if denied:
                return denied
            messages = await a2a_svc.get_full_log(db, limit=limit, project_id=project_id)
            return {"jsonrpc": "2.0", "result": {"tasks": messages}, "id": req_id}

    if method == "tasks/cancel":
        return {"jsonrpc": "2.0", "result": {"status": "canceled"}, "id": req_id}

    if method == "agent/discover":
        project_id = _a2a_project_id(params)
        if not project_id:
            return _a2a_jsonrpc_error(
                400,
                -32602,
                "project_id is required for A2A agent/discover.",
                req_id,
            )

        from app.services import agent_service
        from app.api.agent_project_scope import filter_agent_dicts_for_project

        async with async_session() as db:
            denied = await _authorize_project_scope(
                db,
                request,
                project_id,
                req_id,
                min_role="viewer",
            )
            if denied:
                return denied
            agents = await agent_service.list_agents(db)
            agents = filter_agent_dicts_for_project(agents, project_id, request)
            return {"jsonrpc": "2.0", "result": {"agents": agents}, "id": req_id}

    return _a2a_jsonrpc_error(400, -32601, f"Method not found: {method}", req_id)
