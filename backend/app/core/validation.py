"""Validation Patterns — multi-model/multi-run validation strategies.

Academic foundations:
- Dual-run: Basic inter-rater reliability (2 models)
- Adversarial review: One model critiques another (Du et al., ICML 2024)
- Full ensemble: 3+ models with heuristic consensus metrics inspired by
  Mixture-of-Agents and Fleiss' Kappa
- Self-MoA: Temperature variation on same model (Li et al., 2025)
- Debate rounds: Iterative refinement between models (Du et al., ICML 2024)
"""

import json
import logging
import uuid
from dataclasses import dataclass

from app.core.consensus import ConsensusResult, compute_consensus

logger = logging.getLogger(__name__)


def _server_model_names(server) -> set[str]:
    names: set[str] = set()
    for attr in ("loaded_models", "models", "model_names"):
        raw = getattr(server, attr, None)
        if isinstance(raw, (list, tuple, set)):
            names.update(str(item).strip() for item in raw if str(item).strip())
    capabilities = getattr(server, "model_capabilities", None)
    if isinstance(capabilities, dict):
        names.update(str(name).strip() for name in capabilities if str(name).strip())
    default_model = getattr(server, "default_model", None) or getattr(server, "model", None)
    if default_model:
        names.add(str(default_model).strip())
    return names


def _diverse_servers(servers: list) -> list:
    """Prefer different advertised models, then fill with healthy servers."""
    selected = []
    seen_models: set[str] = set()
    for server in servers:
        names = _server_model_names(server) or {getattr(server, "name", "")}
        if names.isdisjoint(seen_models):
            selected.append(server)
            seen_models.update(names)
    for server in servers:
        if server not in selected:
            selected.append(server)
    return selected


def _route_evidence(result: dict) -> dict:
    route = result.get("_istara_route", {}) if isinstance(result, dict) else {}
    return route if isinstance(route, dict) else {}


def _models_used(route_evidence: list[dict]) -> list[str]:
    return [str(route.get("model", "")) for route in route_evidence if route.get("model")]


def _review_scope(coding_run_id: str | None) -> str:
    return "coded_evidence_review" if coding_run_id else "response_level_quality_signal"


async def _record_review_telemetry(
    *,
    operation: str,
    project_id: str | None,
    trace_id: str | None,
    coding_run_id: str | None,
    evidence_unit_ids: list[str] | None,
    codebook_version_id: str | None,
    route_evidence: list[dict],
    consensus_score: float | None,
    status: str,
    error_type: str | None = None,
    error_message: str | None = None,
) -> None:
    """Record content-free review telemetry only for coded-evidence reviews."""
    if not project_id or not coding_run_id:
        return
    try:
        from app.core.telemetry import telemetry_recorder

        route = route_evidence[0] if route_evidence else {}
        donor_id = str(route.get("node_id") or route.get("donor_id") or "")
        route_id = str(route.get("route_id") or donor_id or "")
        await telemetry_recorder.record_research_validity_event(
            trace_id=trace_id or uuid.uuid4().hex[:36],
            operation=operation,
            project_id=project_id,
            status=status,
            model_name=str(route.get("model") or ""),
            route_id=route_id,
            donor_id=donor_id,
            coding_run_id=coding_run_id,
            evidence_unit_id=(evidence_unit_ids or [""])[0],
            codebook_version_id=codebook_version_id or "",
            consensus_score=consensus_score,
            error_type=error_type,
            error_message=error_message,
        )
    except Exception as exc:
        logger.debug("Research-validity review telemetry skipped: %s", exc)


@dataclass
class ValidationResult:
    """Full result of a validation run."""

    method: str
    consensus: ConsensusResult
    responses: list[str]
    best_response: str
    metadata: dict


async def _dispatch_ensemble(
    *,
    purpose: str,
    messages: list[dict],
    n: int,
    distinct: bool,
    system: str = "",
    temperatures: list[float] | None = None,
    model: str | None = None,
    minimum_n: int | None = None,
    project_id: str | None = None,
) -> tuple[list[str], list[dict], list[str]]:
    """W7 AgenticDispatcher ensemble branch (master plan §8 W7).

    Returns ``(responses, route_evidence, endpoint_ids)`` with failed or empty
    samples filtered out, mirroring the legacy per-server failure tolerance.
    ``distinct=True`` fails closed inside the Pi engine
    (``PiEndpointResolutionError``) when fewer than ``n`` distinct endpoints
    exist — diversity is never fabricated from one endpoint.
    """
    from app.core.agentic import agentic
    from app.core.agentic.types import TurnParams

    outcome = await agentic.ensemble(
        purpose=purpose,
        project_id=project_id or "",
        system=system or None,
        messages=messages,
        n=n,
        distinct=distinct,
        temperatures=temperatures,
        minimum_n=minimum_n,
        params=TurnParams(model=model, temperature=0.7),
        spine_phase="review",
    )
    responses: list[str] = []
    route_evidence: list[dict] = []
    for index, sample in enumerate(outcome.samples):
        endpoint_id = (
            outcome.endpoint_ids[index]
            if index < len(outcome.endpoint_ids)
            else sample.endpoint_id
        ) or ""
        if sample.status != "success" or not sample.text:
            logger.warning(
                "Ensemble %s: sample %d failed (status=%s)", purpose, index, sample.status
            )
            continue
        responses.append(sample.text)
        route_evidence.append(
            {"endpoint_id": endpoint_id, "route_kind": "agentic_ensemble"}
        )
    return responses, route_evidence, list(outcome.endpoint_ids)


async def dual_run(
    prompt: str,
    system: str = "",
    model: str | None = None,
    project_id: str | None = None,
) -> ValidationResult:
    """Run the same prompt on two different servers/models and compare.

    Uses the LLM Router to send to two different endpoints.
    """
    from app.config import settings

    if settings.agentic_core:
        # W7: the dual-run goes through the AgenticDispatcher ensemble verb
        # (``validation.dual_run``); the legacy branch below is preserved for
        # agentic_core=False. distinct=True fails closed: fewer than 2
        # distinct Pi endpoints degrades to the labeled single-model
        # temperature variation, never fabricated diversity from one endpoint.
        from app.core.pi_runtime.endpoints import PiEndpointResolutionError
        from app.core.agentic.types import AgenticDispatchError

        try:
            responses, route_evidence, endpoint_ids = await _dispatch_ensemble(
                purpose="validation.dual_run",
                messages=[{"role": "user", "content": prompt}],
                n=2,
                distinct=True,
                system=system,
                model=model,
                project_id=project_id,
            )
        except PiEndpointResolutionError:
            return await self_moa(
                prompt,
                system=system,
                model=model,
                n=2,
                project_id=project_id,
            )
        except AgenticDispatchError as exc:
            if str(exc) != "insufficient_distinct_legacy_servers":
                logger.warning("Dual-run dispatch failed: %s", exc)
                return _empty_result("dual_run")
            return await self_moa(
                prompt,
                system=system,
                model=model,
                n=2,
                project_id=project_id,
            )
        except Exception as exc:
            logger.warning("Dual-run dispatch failed: %s", exc)
            return _empty_result("dual_run")
        if not responses:
            return _empty_result("dual_run")
        embeddings = await _get_embeddings(responses, project_id=project_id)
        consensus = compute_consensus(responses, embeddings, method="dual_run")
        return ValidationResult(
            method="dual_run",
            consensus=consensus,
            responses=responses,
            best_response=responses[consensus.best_response_idx],
            metadata={
                "endpoint_ids": endpoint_ids,
                "route_evidence": route_evidence,
                "models_used": _models_used(route_evidence),
            },
        )

    from app.core.llm_router import llm_router

    messages = [{"role": "user", "content": prompt}]
    servers = _diverse_servers(
        [s for s in llm_router._sorted_servers(project_id=project_id) if s.is_healthy]
    )

    if len(servers) < 2:
        # Fallback: run twice on same server with different temperatures
        return await self_moa(
            prompt,
            system=system,
            model=model,
            n=2,
            project_id=project_id,
        )

    responses = []
    route_evidence = []
    for server in servers[:2]:
        try:
            msgs = list(messages)
            if system:
                msgs = [{"role": "system", "content": system}, *msgs]
            result = await server.chat(
                msgs,
                model=model,
                temperature=0.7,
                project_id=project_id,
            )
            responses.append(result.get("message", {}).get("content", ""))
            route_evidence.append(_route_evidence(result))
        except Exception as e:
            logger.warning(f"Dual-run: server {server.name} failed: {e}")
            responses.append("")

    responses = [r for r in responses if r]
    if not responses:
        return _empty_result("dual_run")

    # Get embeddings for semantic comparison
    embeddings = await _get_embeddings(responses, project_id=project_id)
    consensus = compute_consensus(responses, embeddings, method="dual_run")

    return ValidationResult(
        method="dual_run",
        consensus=consensus,
        responses=responses,
        best_response=responses[consensus.best_response_idx],
        metadata={
            "servers_used": [s.name for s in servers[:2]],
            "route_evidence": route_evidence,
            "models_used": [r.get("model", "") for r in route_evidence if r],
        },
    )


async def adversarial_review(
    prompt: str,
    initial_response: str,
    system: str = "",
    model: str | None = None,
    project_id: str | None = None,
    coding_run_id: str | None = None,
    evidence_unit_ids: list[str] | None = None,
    codebook_version_id: str | None = None,
    trace_id: str | None = None,
) -> ValidationResult:
    """Have a second model critique the first model's response."""
    from app.config import settings

    review_prompt = (
        f"You are a critical reviewer. Analyze this response for accuracy, "
        f"completeness, and potential issues:\n\n"
        f"Original question: {prompt}\n\n"
        f"Response to review:\n{initial_response}\n\n"
        f"Provide your assessment: is this response accurate and complete? "
        f"Rate agreement 1-5 and explain any disagreements."
    )

    if settings.agentic_core:
        # W7: the critique goes through the AgenticDispatcher completion verb
        # (``validation.adversarial``); the legacy branch below is preserved
        # for agentic_core=False.
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        try:
            outcome = await agentic.completion(
                purpose="validation.adversarial",
                project_id=project_id or "",
                system=system or None,
                messages=[{"role": "user", "content": review_prompt}],
                params=TurnParams(model=model, temperature=0.3),
                spine_phase="review",
            )
            review = outcome.text or ""
            route_evidence = [
                {
                    "endpoint_id": outcome.endpoint_id or "",
                    "route_kind": "agentic_completion",
                }
            ]
        except Exception as e:
            logger.warning(f"Adversarial review failed: {e}")
            await _record_review_telemetry(
                operation="adversarial.review",
                project_id=project_id,
                trace_id=trace_id,
                coding_run_id=coding_run_id,
                evidence_unit_ids=evidence_unit_ids,
                codebook_version_id=codebook_version_id,
                route_evidence=[],
                consensus_score=None,
                status="error",
                error_type="adversarial_review_failed",
                error_message=str(e)[:160],
            )
            return _empty_result("adversarial_review")
    else:
        from app.core.llm_router import llm_router

        messages = [{"role": "user", "content": review_prompt}]
        if system:
            messages = [{"role": "system", "content": system}, *messages]

        try:
            result = await llm_router.chat(
                messages,
                model=model,
                temperature=0.3,
                project_id=project_id,
            )
            review = result.get("message", {}).get("content", "")
            route_evidence = [_route_evidence(result)]
        except Exception as e:
            logger.warning(f"Adversarial review failed: {e}")
            await _record_review_telemetry(
                operation="adversarial.review",
                project_id=project_id,
                trace_id=trace_id,
                coding_run_id=coding_run_id,
                evidence_unit_ids=evidence_unit_ids,
                codebook_version_id=codebook_version_id,
                route_evidence=[],
                consensus_score=None,
                status="error",
                error_type="adversarial_review_failed",
                error_message=str(e)[:160],
            )
            return _empty_result("adversarial_review")

    responses = [initial_response, review]
    embeddings = await _get_embeddings(responses, project_id=project_id)
    consensus = compute_consensus(responses, embeddings, method="adversarial_review")
    await _record_review_telemetry(
        operation="adversarial.review",
        project_id=project_id,
        trace_id=trace_id,
        coding_run_id=coding_run_id,
        evidence_unit_ids=evidence_unit_ids,
        codebook_version_id=codebook_version_id,
        route_evidence=route_evidence,
        consensus_score=consensus.agreement_score,
        status="success",
    )

    return ValidationResult(
        method="adversarial_review",
        consensus=consensus,
        responses=responses,
        best_response=initial_response,  # Original response is the primary output
        metadata={
            "review_text": review,
            "route_evidence": route_evidence,
            "models_used": _models_used(route_evidence),
            "validation_scope": _review_scope(coding_run_id),
            "formal_reliability": False,
            "coding_run_id": coding_run_id or "",
            "evidence_unit_ids": evidence_unit_ids or [],
            "codebook_version_id": codebook_version_id or "",
        },
    )


async def full_ensemble(
    prompt: str,
    system: str = "",
    model: str | None = None,
    min_responses: int = 3,
    project_id: str | None = None,
) -> ValidationResult:
    """Run prompt across 3+ models/servers for full ensemble consensus."""
    from app.config import settings

    if settings.agentic_core:
        # W7: the ensemble goes through the AgenticDispatcher ensemble verb
        # (``validation.full_ensemble``, n=min_responses+1 distinct endpoints);
        # the legacy branch below is preserved for agentic_core=False.
        # distinct=True fails closed: fewer distinct Pi endpoints than
        # requested degrades down the existing chain (dual_run -> self_moa),
        # never fabricated diversity from fewer endpoints.
        from app.core.pi_runtime.endpoints import PiEndpointResolutionError
        from app.core.agentic.types import AgenticDispatchError

        try:
            responses, route_evidence, endpoint_ids = await _dispatch_ensemble(
                purpose="validation.full_ensemble",
                messages=[{"role": "user", "content": prompt}],
                n=min_responses + 1,
                distinct=True,
                minimum_n=min_responses,
                system=system,
                model=model,
                project_id=project_id,
            )
        except PiEndpointResolutionError:
            return await dual_run(
                prompt,
                system=system,
                model=model,
                project_id=project_id,
            )
        except AgenticDispatchError as exc:
            if str(exc) != "insufficient_distinct_legacy_servers":
                logger.warning("Full-ensemble dispatch failed: %s", exc)
                return _empty_result("full_ensemble")
            return await dual_run(
                prompt,
                system=system,
                model=model,
                project_id=project_id,
            )
        except Exception as exc:
            logger.warning("Full-ensemble dispatch failed: %s", exc)
            return _empty_result("full_ensemble")
        if not responses:
            return _empty_result("full_ensemble")
        embeddings = await _get_embeddings(responses, project_id=project_id)
        consensus = compute_consensus(responses, embeddings, method="full_ensemble")
        return ValidationResult(
            method="full_ensemble",
            consensus=consensus,
            responses=responses,
            best_response=responses[consensus.best_response_idx],
            metadata={
                "endpoint_ids": endpoint_ids,
                "n_responses": len(responses),
                "route_evidence": route_evidence,
                "models_used": _models_used(route_evidence),
            },
        )

    from app.core.llm_router import llm_router

    servers = _diverse_servers(
        [s for s in llm_router._sorted_servers(project_id=project_id) if s.is_healthy]
    )

    if len(servers) < min_responses:
        if len(servers) >= 2:
            return await dual_run(
                prompt,
                system=system,
                model=model,
                project_id=project_id,
            )
        # Self-MoA is the constrained fallback when project compute has only
        # one healthy model endpoint available.
        return await self_moa(
            prompt,
            system=system,
            model=model,
            n=min_responses,
            project_id=project_id,
        )

    responses = []
    route_evidence = []
    server_names = []
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    for server in servers[:min_responses + 1]:  # Try one extra in case of failure
        if len(responses) >= min_responses:
            break
        try:
            result = await server.chat(
                messages,
                model=model,
                temperature=0.7,
                project_id=project_id,
            )
            content = result.get("message", {}).get("content", "")
            if content:
                responses.append(content)
                server_names.append(server.name)
                route_evidence.append(_route_evidence(result))
        except Exception as e:
            logger.warning(f"Ensemble: server {server.name} failed: {e}")

    if not responses:
        return _empty_result("full_ensemble")

    embeddings = await _get_embeddings(responses, project_id=project_id)
    consensus = compute_consensus(responses, embeddings, method="full_ensemble")

    return ValidationResult(
        method="full_ensemble",
        consensus=consensus,
        responses=responses,
        best_response=responses[consensus.best_response_idx],
        metadata={
            "servers_used": server_names,
            "n_responses": len(responses),
            "route_evidence": route_evidence,
            "models_used": [r.get("model", "") for r in route_evidence if r],
        },
    )


async def self_moa(
    prompt: str,
    system: str = "",
    model: str | None = None,
    n: int = 3,
    project_id: str | None = None,
) -> ValidationResult:
    """Self Mixture-of-Agents: same model, different temperatures.

    Reference: Li et al. (2025). Self-MoA.
    """
    temperatures = [0.3, 0.7, 1.0][:n]
    if n > 3:
        temperatures.extend([0.5, 0.9][: n - 3])

    from app.config import settings

    if settings.agentic_core:
        # W7: the temperature sweep goes through the AgenticDispatcher
        # ensemble verb (``validation.self_moa``, distinct=False — n samples
        # on one admitted endpoint); the legacy branch below is preserved for
        # agentic_core=False.
        try:
            responses, route_evidence, endpoint_ids = await _dispatch_ensemble(
                purpose="validation.self_moa",
                messages=[{"role": "user", "content": prompt}],
                n=len(temperatures),
                distinct=False,
                temperatures=temperatures,
                system=system,
                model=model,
                project_id=project_id,
            )
        except Exception as exc:
            logger.warning("Self-MoA dispatch failed: %s", exc)
            return _empty_result("self_moa")
        if not responses:
            return _empty_result("self_moa")
        embeddings = await _get_embeddings(responses, project_id=project_id)
        consensus = compute_consensus(responses, embeddings, method="self_moa")
        return ValidationResult(
            method="self_moa",
            consensus=consensus,
            responses=responses,
            best_response=responses[consensus.best_response_idx],
            metadata={
                "temperatures": temperatures[: len(responses)],
                "endpoint_ids": endpoint_ids,
                "route_evidence": route_evidence,
                "assurance": "single_model_temperature_variation",
            },
        )

    from app.core.llm_router import llm_router

    responses = []
    route_evidence = []
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    for temp in temperatures:
        try:
            result = await llm_router.chat(
                messages,
                model=model,
                temperature=temp,
                project_id=project_id,
            )
            content = result.get("message", {}).get("content", "")
            if content:
                responses.append(content)
                route_evidence.append(_route_evidence(result))
        except Exception as e:
            logger.warning(f"Self-MoA: temperature {temp} failed: {e}")

    if not responses:
        return _empty_result("self_moa")

    embeddings = await _get_embeddings(responses, project_id=project_id)
    consensus = compute_consensus(responses, embeddings, method="self_moa")

    return ValidationResult(
        method="self_moa",
        consensus=consensus,
        responses=responses,
        best_response=responses[consensus.best_response_idx],
        metadata={
            "temperatures": temperatures[:len(responses)],
            "route_evidence": route_evidence,
            "assurance": "single_model_temperature_variation",
        },
    )


async def debate_rounds(
    prompt: str,
    system: str = "",
    model: str | None = None,
    rounds: int = 2,
    project_id: str | None = None,
    coding_run_id: str | None = None,
    evidence_unit_ids: list[str] | None = None,
    codebook_version_id: str | None = None,
    trace_id: str | None = None,
) -> ValidationResult:
    """Multi-round debate between models.

    Reference: Du et al. (2024). Multi-Agent Debate. ICML 2024.
    """
    from app.config import settings

    if settings.agentic_core:
        # W7: the initial response and each debate round go through the
        # AgenticDispatcher completion verb (``validation.debate``); the
        # legacy branch below is preserved for agentic_core=False.
        from app.core.agentic import agentic
        from app.core.agentic.types import TurnParams

        messages = [{"role": "user", "content": prompt}]
        all_responses = []
        route_evidence = []

        # Initial response
        try:
            outcome = await agentic.completion(
                purpose="validation.debate",
                project_id=project_id or "",
                system=system or None,
                messages=messages,
                params=TurnParams(model=model, temperature=0.7),
                spine_phase="review",
            )
            current = outcome.text or ""
            all_responses.append(current)
            route_evidence.append(
                {
                    "endpoint_id": outcome.endpoint_id or "",
                    "route_kind": "agentic_completion",
                }
            )
        except Exception as e:
            logger.warning(f"Debate: initial response failed: {e}")
            await _record_review_telemetry(
                operation="debate.review",
                project_id=project_id,
                trace_id=trace_id,
                coding_run_id=coding_run_id,
                evidence_unit_ids=evidence_unit_ids,
                codebook_version_id=codebook_version_id,
                route_evidence=[],
                consensus_score=None,
                status="error",
                error_type="debate_review_failed",
                error_message=str(e)[:160],
            )
            return _empty_result("debate_rounds")

        # Debate rounds
        for round_num in range(rounds):
            debate_prompt = (
                f"Previous response:\n{current}\n\n"
                f"Do you agree with this response? If not, provide a better answer. "
                f"If you agree, confirm and add any missing points."
            )
            debate_messages = [
                *messages,
                {"role": "assistant", "content": current},
                {"role": "user", "content": debate_prompt},
            ]
            try:
                outcome = await agentic.completion(
                    purpose="validation.debate",
                    project_id=project_id or "",
                    system=system or None,
                    messages=debate_messages,
                    params=TurnParams(model=model, temperature=0.5),
                    spine_phase="review",
                )
                current = outcome.text or ""
                all_responses.append(current)
                route_evidence.append(
                    {
                        "endpoint_id": outcome.endpoint_id or "",
                        "route_kind": "agentic_completion",
                    }
                )
            except Exception as e:
                logger.warning(f"Debate round {round_num + 1} failed: {e}")
                break

        embeddings = await _get_embeddings(all_responses, project_id=project_id)
        consensus = compute_consensus(all_responses, embeddings, method="debate_rounds")
        await _record_review_telemetry(
            operation="debate.review",
            project_id=project_id,
            trace_id=trace_id,
            coding_run_id=coding_run_id,
            evidence_unit_ids=evidence_unit_ids,
            codebook_version_id=codebook_version_id,
            route_evidence=route_evidence,
            consensus_score=consensus.agreement_score,
            status="success",
        )

        return ValidationResult(
            method="debate_rounds",
            consensus=consensus,
            responses=all_responses,
            best_response=all_responses[-1],  # Last round is most refined
            metadata={
                "rounds_completed": len(all_responses) - 1,
                "route_evidence": route_evidence,
                "models_used": _models_used(route_evidence),
                "validation_scope": _review_scope(coding_run_id),
                "formal_reliability": False,
                "coding_run_id": coding_run_id or "",
                "evidence_unit_ids": evidence_unit_ids or [],
                "codebook_version_id": codebook_version_id or "",
            },
        )

    from app.core.llm_router import llm_router

    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    all_responses = []
    route_evidence = []

    # Initial response
    try:
        result = await llm_router.chat(
            messages,
            model=model,
            temperature=0.7,
            project_id=project_id,
        )
        current = result.get("message", {}).get("content", "")
        all_responses.append(current)
        route_evidence.append(_route_evidence(result))
    except Exception as e:
        logger.warning(f"Debate: initial response failed: {e}")
        await _record_review_telemetry(
            operation="debate.review",
            project_id=project_id,
            trace_id=trace_id,
            coding_run_id=coding_run_id,
            evidence_unit_ids=evidence_unit_ids,
            codebook_version_id=codebook_version_id,
            route_evidence=[],
            consensus_score=None,
            status="error",
            error_type="debate_review_failed",
            error_message=str(e)[:160],
        )
        return _empty_result("debate_rounds")

    # Debate rounds
    for round_num in range(rounds):
        debate_prompt = (
            f"Previous response:\n{current}\n\n"
            f"Do you agree with this response? If not, provide a better answer. "
            f"If you agree, confirm and add any missing points."
        )
        debate_messages = [
            *messages,
            {"role": "assistant", "content": current},
            {"role": "user", "content": debate_prompt},
        ]
        try:
            result = await llm_router.chat(
                debate_messages,
                model=model,
                temperature=0.5,
                project_id=project_id,
            )
            current = result.get("message", {}).get("content", "")
            all_responses.append(current)
            route_evidence.append(_route_evidence(result))
        except Exception as e:
            logger.warning(f"Debate round {round_num + 1} failed: {e}")
            break

    embeddings = await _get_embeddings(all_responses, project_id=project_id)
    consensus = compute_consensus(all_responses, embeddings, method="debate_rounds")
    await _record_review_telemetry(
        operation="debate.review",
        project_id=project_id,
        trace_id=trace_id,
        coding_run_id=coding_run_id,
        evidence_unit_ids=evidence_unit_ids,
        codebook_version_id=codebook_version_id,
        route_evidence=route_evidence,
        consensus_score=consensus.agreement_score,
        status="success",
    )

    return ValidationResult(
        method="debate_rounds",
        consensus=consensus,
        responses=all_responses,
        best_response=all_responses[-1],  # Last round is most refined
        metadata={
            "rounds_completed": len(all_responses) - 1,
            "route_evidence": route_evidence,
            "models_used": _models_used(route_evidence),
            "validation_scope": _review_scope(coding_run_id),
            "formal_reliability": False,
            "coding_run_id": coding_run_id or "",
            "evidence_unit_ids": evidence_unit_ids or [],
            "codebook_version_id": codebook_version_id or "",
        },
    )


async def _get_embeddings(
    texts: list[str],
    project_id: str | None = None,
) -> list[list[float]]:
    """Get embeddings for texts through the AgenticDispatcher (W8).

    Project-scoped: the dispatcher resolves the engine per the project's
    ``agentic_engine`` setting — legacy: the unchanged ``ollama.embed*``
    plane; Pi: the W8 EmbeddingsGateway. Consensus similarity degrades to
    the existing empty-embedding handling on any failure.
    """
    try:
        from app.core.agentic import agentic
        return await agentic.embed(texts=texts, project_id=project_id)
    except Exception:
        return []


def _empty_result(method: str) -> ValidationResult:
    from app.core.consensus import ConsensusResult
    return ValidationResult(
        method=method,
        consensus=ConsensusResult(
            method=method,
            agreement_score=0,
            kappa=None,
            cosine_sim=None,
            confidence="insufficient",
            best_response_idx=0,
            per_response_scores=[],
            details={"error": "No valid responses obtained"},
        ),
        responses=[],
        best_response="",
        metadata={"error": "Validation failed — no responses"},
    )
