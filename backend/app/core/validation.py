"""Validation Patterns — multi-model/multi-run validation strategies.

Academic foundations:
- Dual-run: Basic inter-rater reliability (2 models)
- Adversarial review: One model critiques another (Du et al., ICML 2024)
- Full ensemble: 3+ models with Fleiss' Kappa (Wang et al., ICLR 2025)
- Self-MoA: Temperature variation on same model (Li et al., 2025)
- Debate rounds: Iterative refinement between models (Du et al., ICML 2024)
"""

import json
import logging
from dataclasses import dataclass

from app.core.consensus import ConsensusResult, compute_consensus

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Full result of a validation run."""

    method: str
    consensus: ConsensusResult
    responses: list[str]
    best_response: str
    metadata: dict


async def dual_run(prompt: str, system: str = "", model: str | None = None) -> ValidationResult:
    """Run the same prompt on two different servers/models and compare.

    Uses the LLM Router to send to two different endpoints.
    """
    from app.core.llm_router import llm_router

    messages = [{"role": "user", "content": prompt}]
    servers = [s for s in llm_router._sorted_servers() if s.is_healthy]

    if len(servers) < 2:
        # Fallback: run twice on same server with different temperatures
        return await self_moa(prompt, system=system, model=model, n=2)

    responses = []
    for server in servers[:2]:
        try:
            msgs = list(messages)
            if system:
                msgs = [{"role": "system", "content": system}, *msgs]
            result = await server.chat(msgs, model=model, temperature=0.7)
            responses.append(result.get("message", {}).get("content", ""))
        except Exception as e:
            logger.warning(f"Dual-run: server {server.name} failed: {e}")
            responses.append("")

    responses = [r for r in responses if r]
    if not responses:
        return _empty_result("dual_run")

    # Get embeddings for semantic comparison
    embeddings = await _get_embeddings(responses)
    consensus = compute_consensus(responses, embeddings, method="dual_run")

    return ValidationResult(
        method="dual_run",
        consensus=consensus,
        responses=responses,
        best_response=responses[consensus.best_response_idx],
        metadata={"servers_used": [s.name for s in servers[:2]]},
    )


async def adversarial_review(
    prompt: str, initial_response: str, system: str = "", model: str | None = None
) -> ValidationResult:
    """Have a second model critique the first model's response."""
    from app.core.llm_router import llm_router

    review_prompt = (
        f"You are a critical reviewer. Analyze this response for accuracy, "
        f"completeness, and potential issues:\n\n"
        f"Original question: {prompt}\n\n"
        f"Response to review:\n{initial_response}\n\n"
        f"Provide your assessment: is this response accurate and complete? "
        f"Rate agreement 1-5 and explain any disagreements."
    )

    messages = [{"role": "user", "content": review_prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    try:
        result = await llm_router.chat(messages, model=model, temperature=0.3)
        review = result.get("message", {}).get("content", "")
    except Exception as e:
        logger.warning(f"Adversarial review failed: {e}")
        return _empty_result("adversarial_review")

    responses = [initial_response, review]
    embeddings = await _get_embeddings(responses)
    consensus = compute_consensus(responses, embeddings, method="adversarial_review")

    return ValidationResult(
        method="adversarial_review",
        consensus=consensus,
        responses=responses,
        best_response=initial_response,  # Original response is the primary output
        metadata={"review_text": review},
    )


async def full_ensemble(
    prompt: str, system: str = "", model: str | None = None, min_responses: int = 3
) -> ValidationResult:
    """Run prompt across 3+ models/servers for full ensemble consensus."""
    from app.core.llm_router import llm_router

    servers = [s for s in llm_router._sorted_servers() if s.is_healthy]

    if len(servers) < min_responses:
        # Supplement with temperature variation
        return await self_moa(prompt, system=system, model=model, n=min_responses)

    responses = []
    server_names = []
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    for server in servers[:min_responses + 1]:  # Try one extra in case of failure
        if len(responses) >= min_responses:
            break
        try:
            result = await server.chat(messages, model=model, temperature=0.7)
            content = result.get("message", {}).get("content", "")
            if content:
                responses.append(content)
                server_names.append(server.name)
        except Exception as e:
            logger.warning(f"Ensemble: server {server.name} failed: {e}")

    if not responses:
        return _empty_result("full_ensemble")

    embeddings = await _get_embeddings(responses)
    consensus = compute_consensus(responses, embeddings, method="full_ensemble")

    return ValidationResult(
        method="full_ensemble",
        consensus=consensus,
        responses=responses,
        best_response=responses[consensus.best_response_idx],
        metadata={"servers_used": server_names, "n_responses": len(responses)},
    )


async def self_moa(
    prompt: str, system: str = "", model: str | None = None, n: int = 3
) -> ValidationResult:
    """Self Mixture-of-Agents: same model, different temperatures.

    Reference: Li et al. (2025). Self-MoA.
    """
    from app.core.llm_router import llm_router

    temperatures = [0.3, 0.7, 1.0][:n]
    if n > 3:
        temperatures.extend([0.5, 0.9][: n - 3])

    responses = []
    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    for temp in temperatures:
        try:
            result = await llm_router.chat(messages, model=model, temperature=temp)
            content = result.get("message", {}).get("content", "")
            if content:
                responses.append(content)
        except Exception as e:
            logger.warning(f"Self-MoA: temperature {temp} failed: {e}")

    if not responses:
        return _empty_result("self_moa")

    embeddings = await _get_embeddings(responses)
    consensus = compute_consensus(responses, embeddings, method="self_moa")

    return ValidationResult(
        method="self_moa",
        consensus=consensus,
        responses=responses,
        best_response=responses[consensus.best_response_idx],
        metadata={"temperatures": temperatures[:len(responses)]},
    )


async def debate_rounds(
    prompt: str, system: str = "", model: str | None = None, rounds: int = 2
) -> ValidationResult:
    """Multi-round debate between models.

    Reference: Du et al. (2024). Multi-Agent Debate. ICML 2024.
    """
    from app.core.llm_router import llm_router

    messages = [{"role": "user", "content": prompt}]
    if system:
        messages = [{"role": "system", "content": system}, *messages]

    all_responses = []

    # Initial response
    try:
        result = await llm_router.chat(messages, model=model, temperature=0.7)
        current = result.get("message", {}).get("content", "")
        all_responses.append(current)
    except Exception as e:
        logger.warning(f"Debate: initial response failed: {e}")
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
            result = await llm_router.chat(debate_messages, model=model, temperature=0.5)
            current = result.get("message", {}).get("content", "")
            all_responses.append(current)
        except Exception as e:
            logger.warning(f"Debate round {round_num + 1} failed: {e}")
            break

    embeddings = await _get_embeddings(all_responses)
    consensus = compute_consensus(all_responses, embeddings, method="debate_rounds")

    return ValidationResult(
        method="debate_rounds",
        consensus=consensus,
        responses=all_responses,
        best_response=all_responses[-1],  # Last round is most refined
        metadata={"rounds_completed": len(all_responses) - 1},
    )


async def _get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings for texts using the LLM router."""
    try:
        from app.core.llm_router import llm_router
        return await llm_router.embed_batch(texts)
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
