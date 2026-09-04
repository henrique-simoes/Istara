"""Pi coder dispatch, route-evidence postprocessing, and the bounded Qwen rate-limit fallback chains."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.research_validity import (
    QUALITATIVE_CODING_PROTOCOL,
)
from app.services.research_validity_schemas import (
    CODING_CORE_RESPONSE_SCHEMA,
    CODING_RESPONSE_SCHEMA,
    DASHSCOPE_COMPAT_BASE_URL,
    QWEN_RATE_LIMIT_FALLBACK_CHAINS,
    CoderRunner,
    CoderSpec,
    QwenRateLimitFallbackError,
)

logger = logging.getLogger(__name__)


def _pi_endpoint_identity(endpoint: Any) -> tuple[str, ...]:
    """Return non-secret fields that define one selected Pi endpoint."""
    return (
        str(getattr(endpoint, "endpoint_id", "") or ""),
        str(getattr(endpoint, "provider_kind", "") or ""),
        str(getattr(endpoint, "base_url", "") or ""),
        str(getattr(endpoint, "model", "") or ""),
        str(getattr(endpoint, "provider_account_handle", "") or ""),
        str(getattr(endpoint, "kind", "") or ""),
    )


def _is_qwen_rate_limit_error(exc: BaseException) -> bool:
    """Recognize provider throttling without treating every failure as retryable."""
    messages: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        messages.append(str(current))
        current = current.__cause__ or current.__context__
    return bool(
        re.search(
            r"(?:(?<!\d)429(?!\d)|too[\s_-]+many[\s_-]+requests|rate[\s_-]*limit|throttl)",
            " ".join(messages),
            re.IGNORECASE,
        )
    )


def _is_dashscope_endpoint(endpoint: Any) -> bool:
    """Return true only for the regular Singapore DashScope OpenAI wire path."""
    return (
        str(getattr(endpoint, "provider_kind", "") or "").strip().lower() == "openai_compat"
        and str(getattr(endpoint, "pi_provider", "") or "").strip().lower() == "dashscope"
        and str(getattr(endpoint, "base_url", "") or "").strip().rstrip("/")
        == DASHSCOPE_COMPAT_BASE_URL
    )


def _same_dashscope_key(original: Any, fallback: Any) -> bool:
    """Require one non-empty API key and endpoint before changing model identity."""
    return bool(
        _is_dashscope_endpoint(original)
        and _is_dashscope_endpoint(fallback)
        and str(getattr(original, "api_key", "") or "")
        and str(getattr(original, "api_key", "")) == str(getattr(fallback, "api_key", ""))
    )


def _fallback_coder(coder: CoderSpec, endpoint: Any) -> CoderSpec:
    from types import SimpleNamespace

    return CoderSpec(
        node=SimpleNamespace(
            node_id=endpoint.endpoint_id,
            name=endpoint.endpoint_id,
            source="pi",
            provider_type=endpoint.provider_kind,
            endpoint_id=endpoint.endpoint_id,
            provider_account_handle=getattr(endpoint, "provider_account_handle", ""),
        ),
        coder_id=f"model-coder:{endpoint.endpoint_id}",
        model_name=endpoint.model,
        pi_manager=coder.pi_manager,
        pi_service=coder.pi_service,
        pi_endpoint_identity=_pi_endpoint_identity(endpoint),
    )


def _merge_coding_route_evidence(previous_response: dict, replacement_response: dict) -> dict:
    """Keep fallback provenance when a bounded coding repair replaces output.

    A repair is a second provider call for the same coder slot.  Its response
    route is authoritative for the accepted application payload, but it must
    not erase an earlier rate-limit chain that selected the active model.  If
    the repair itself falls back, both call-level chains are retained in one
    ordered attempt list and a compact history records their boundaries.
    """
    previous_route = dict(previous_response.get("_istara_route", {}) or {})
    replacement_route = dict(replacement_response.get("_istara_route", {}) or {})
    previous_attempts = previous_route.get("fallback_attempts")
    if not isinstance(previous_attempts, list) or not previous_attempts:
        return replacement_response

    replacement_attempts = replacement_route.get("fallback_attempts")
    if not isinstance(replacement_attempts, list):
        replacement_attempts = []
    merged_route = {**previous_route, **replacement_route}
    merged_route["fallback_attempts"] = [*previous_attempts, *replacement_attempts]
    merged_route["initial_requested_model"] = previous_route.get("requested_model", "")
    merged_route["initial_requested_coder_id"] = previous_route.get("requested_coder_id", "")
    history = [
        {
            "requested_model": previous_route.get("requested_model", ""),
            "served_model": previous_route.get("served_model", ""),
            "fallback_attempts": previous_attempts,
        }
    ]
    if replacement_attempts:
        history.append(
            {
                "requested_model": replacement_route.get("requested_model", ""),
                "served_model": replacement_route.get("served_model", ""),
                "fallback_attempts": replacement_attempts,
            }
        )
    merged_route["fallback_history"] = history
    return {**replacement_response, "_istara_route": merged_route}


async def _run_pi_coder_with_qwen_fallback(
    coder: CoderSpec,
    messages: list[dict],
    model_name: str | None,
    project_id: str,
    *,
    runner: CoderRunner,
) -> tuple[dict, CoderSpec]:
    """Run one coder, advancing only a DashScope Qwen slot after a 429.

    Fallback endpoints are resolved through the same PiModelManager and must
    use the same DashScope base URL and API key. Every attempt is returned in
    route evidence; auth, transport, malformed, and application failures are
    never reclassified as rate limits.
    """
    requested_model = str(model_name or coder.model_name or "").strip()
    fallback_chain = QWEN_RATE_LIMIT_FALLBACK_CHAINS.get(requested_model)
    if fallback_chain is None:
        return await runner(coder, messages, model_name, project_id), coder
    manager = coder.pi_manager
    if manager is None:
        return await runner(coder, messages, model_name, project_id), coder

    await manager.ensure_db_projection()
    selected_endpoint_id = str(getattr(coder.node, "endpoint_id", "") or "").strip()
    original_endpoint = manager.resolve(
        endpoint_id=selected_endpoint_id or None,
        model=requested_model,
        project_id=project_id,
    )
    if not _is_dashscope_endpoint(original_endpoint):
        return await runner(coder, messages, model_name, project_id), coder

    attempts: list[dict[str, str]] = []
    active_coder = coder
    original_endpoint_for_key = original_endpoint
    for index, candidate_model in enumerate(fallback_chain):
        if index == 0:
            endpoint = original_endpoint
        else:
            try:
                endpoint = manager.resolve(model=candidate_model, project_id=project_id)
            except Exception as exc:
                attempts.append(
                    {
                        "model": candidate_model,
                        "endpoint_id": "",
                        "outcome": "unavailable",
                    }
                )
                raise QwenRateLimitFallbackError(
                    f"qwen_rate_limit_fallback_unavailable:{candidate_model}",
                    attempts=attempts,
                ) from exc
            if str(getattr(endpoint, "model", "") or "").strip() != candidate_model:
                attempts.append(
                    {
                        "model": candidate_model,
                        "endpoint_id": str(getattr(endpoint, "endpoint_id", "") or ""),
                        "outcome": "identity_mismatch",
                    }
                )
                raise QwenRateLimitFallbackError(
                    f"qwen_rate_limit_fallback_identity_mismatch:{candidate_model}",
                    attempts=attempts,
                )
            if not _same_dashscope_key(original_endpoint_for_key, endpoint):
                attempts.append(
                    {
                        "model": candidate_model,
                        "endpoint_id": str(getattr(endpoint, "endpoint_id", "") or ""),
                        "outcome": "same_key_mismatch",
                    }
                )
                raise QwenRateLimitFallbackError(
                    f"qwen_rate_limit_fallback_same_key_mismatch:{candidate_model}",
                    attempts=attempts,
                )
            active_coder = _fallback_coder(coder, endpoint)

        endpoint_id = str(getattr(endpoint, "endpoint_id", "") or "").strip()
        try:
            response = await runner(
                active_coder,
                messages,
                active_coder.model_name or None,
                project_id,
            )
        except Exception as exc:
            if not _is_qwen_rate_limit_error(exc):
                raise
            attempts.append(
                {
                    "model": candidate_model,
                    "endpoint_id": endpoint_id,
                    "outcome": "rate_limited",
                }
            )
            if index == len(fallback_chain) - 1:
                raise QwenRateLimitFallbackError(
                    "qwen_rate_limit_fallback_exhausted", attempts=attempts
                ) from exc
            continue

        attempts.append({"model": candidate_model, "endpoint_id": endpoint_id, "outcome": "served"})
        if len(attempts) > 1:
            route = dict(response.get("_istara_route", {}) or {})
            route.update(
                {
                    "requested_model": requested_model,
                    "requested_coder_id": coder.coder_id,
                    "fallback_reason": "rate_limit",
                    "fallback_index": index,
                    "fallback_same_key_verified": True,
                    "fallback_attempts": attempts,
                }
            )
            response = {**response, "_istara_route": route}
        return response, active_coder
    raise AssertionError("unreachable")


async def _pi_coder_runner(
    coder: CoderSpec,
    messages: list[dict],
    model_name: str | None,
    project_id: str,
) -> dict:
    """W7 coder runner: structured dispatch pinned to the coder's exact endpoint."""
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    selected_endpoint_id = str(getattr(coder.node, "endpoint_id", "") or "").strip()
    if coder.pi_manager is not None and selected_endpoint_id:
        # Refresh dynamic projections and resolve against the same manager
        # used for selection. Any removal or identity mutation is rejected
        # before the provider call can create a rater or route record.
        await coder.pi_manager.ensure_db_projection()
        current_endpoint = coder.pi_manager.resolve(
            endpoint_id=selected_endpoint_id,
            model=model_name,
            project_id=project_id,
        )
        if coder.pi_endpoint_identity != _pi_endpoint_identity(current_endpoint):
            raise ValueError(
                "Pi coder catalog drift: selected endpoint identity changed "
                f"for {selected_endpoint_id!r}"
            )

    params = TurnParams(
        temperature=0.2,
        # The governed coding plane must use the requested reasoning path for
        # both DashScope Qwen and the Codex Luna rater.
        thinking_mode="high",
        model=model_name,
        endpoint_id=getattr(coder.node, "endpoint_id", None),
    )
    structured_schema_repair = ""
    try:
        outcome = await agentic.structured(
            purpose="validity.coder",
            project_id=project_id,
            system=None,
            messages=messages,
            schema=CODING_RESPONSE_SCHEMA,
            params=params,
            engine="pi",
            spine_phase="execution",
            **({"pi_service": coder.pi_service} if coder.pi_service is not None else {}),
        )
    except Exception as exc:
        from app.core.pi_runtime.endpoints import PiRuntimeTurnError

        if not isinstance(exc, PiRuntimeTurnError) or exc.error != "structured_output_missing":
            raise
        try:
            outcome = await agentic.structured(
                purpose="validity.coder",
                project_id=project_id,
                system=None,
                messages=messages,
                schema=CODING_CORE_RESPONSE_SCHEMA,
                params=params,
                engine="pi",
                spine_phase="execution",
                repair=False,
                **({"pi_service": coder.pi_service} if coder.pi_service is not None else {}),
            )
            structured_schema_repair = "core_schema"
        except Exception as core_exc:
            # Live provider evidence (L-490): some reasoning models never make
            # the forced structured call under high reasoning effort with a
            # large coding payload, even against the bounded core schema. One
            # final mechanically forced call with reasoning disabled is the
            # last governed attempt; the route evidence discloses it and
            # every other typed failure still propagates unchanged.
            if (
                not isinstance(core_exc, PiRuntimeTurnError)
                or core_exc.error != "structured_output_missing"
            ):
                raise
            off_params = TurnParams(
                temperature=params.temperature,
                thinking_mode="off",
                model=params.model,
                endpoint_id=params.endpoint_id,
            )
            outcome = await agentic.structured(
                purpose="validity.coder",
                project_id=project_id,
                system=None,
                messages=messages,
                schema=CODING_CORE_RESPONSE_SCHEMA,
                params=off_params,
                engine="pi",
                spine_phase="execution",
                repair=False,
                **({"pi_service": coder.pi_service} if coder.pi_service is not None else {}),
            )
            structured_schema_repair = "core_schema_thinking_off"
    served_endpoint_id = str(getattr(outcome, "endpoint_id", "") or "").strip()
    if selected_endpoint_id and served_endpoint_id and served_endpoint_id != selected_endpoint_id:
        # The endpoint is part of the source-of-truth route evidence.  A
        # provider or adapter that reports a different endpoint than the one
        # pinned in TurnParams must not be allowed to masquerade as the
        # selected independent coder; fail closed before any coding rows are
        # persisted or reliability is evaluated.
        raise ValueError(
            "Pi coder endpoint mismatch: selected "
            f"{selected_endpoint_id!r}, served {served_endpoint_id!r}"
        )
    selected_model = str(model_name or getattr(coder, "model_name", "") or "").strip()
    # Research validity requires provider-reported response identity. The
    # dispatcher keeps `model` as the configured/request identity, so using it
    # here would allow a proxy or relay to masquerade as an independent coder.
    served_model = str(getattr(outcome, "served_model", "") or "").strip()
    if selected_model and served_model != selected_model:
        # Model identity is the scientific independence boundary.  The
        # request parameter is not proof of what a provider actually served;
        # a missing or different identity must therefore block the coder
        # before its applications can enter the reliability matrix.
        reason = (
            "missing"
            if not served_model
            else f"selected {selected_model!r}, served {served_model!r}"
        )
        raise ValueError(f"Pi coder model mismatch: {reason}")
    route = dict(getattr(outcome, "route_evidence", {}) or {})
    route_model = str(route.get("model") or "").strip()
    route_served_model = str(route.get("served_model") or "").strip()
    if route_model and route_model != served_model:
        raise ValueError(
            f"Pi coder route model mismatch: route {route_model!r}, served {served_model!r}"
        )
    if route_served_model and route_served_model != served_model:
        raise ValueError(
            "Pi coder route served-model mismatch: route "
            f"{route_served_model!r}, served {served_model!r}"
        )
    route.setdefault("node_id", getattr(coder.node, "node_id", ""))
    route.setdefault("node_source", getattr(coder.node, "source", ""))
    route.setdefault("provider_type", getattr(coder.node, "provider_type", ""))
    route["model"] = served_model
    # Preserve the provider-reported identity alongside the normalized route
    # model.  The latter is persisted for compatibility, while the explicit
    # receipt is the Research Spine's independence boundary and must survive
    # into coding-run evidence for downstream validation.
    route["served_model"] = served_model
    route.setdefault("endpoint_id", served_endpoint_id or selected_endpoint_id)
    route.setdefault("route_kind", "coding_run")
    route.setdefault("outcome", "served")
    if structured_schema_repair:
        route["structured_schema_repair"] = structured_schema_repair
    if structured_schema_repair == "core_schema_thinking_off":
        route["structured_thinking_fallback"] = "off"
    return {
        "message": {"content": json.dumps(outcome.value)},
        "_istara_route": {
            **route,
            "provider_account_handle": (
                route.get("provider_account_handle")
                or getattr(coder.node, "provider_account_handle", "")
            ),
            "decoding_profile": route.get("decoding_profile") or {"temperature": 0.2},
            "protocol_version": route.get("protocol_version")
            or QUALITATIVE_CODING_PROTOCOL["version"],
            "conversation_scope": route.get("conversation_scope") or "fresh_session_per_coder_call",
            "cache_scope": route.get("cache_scope") or "provider_prefix_cache_no_response_reuse",
        },
    }
