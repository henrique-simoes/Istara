"""Self-checking system — verify claims against sources, score confidence."""

from dataclasses import dataclass, field
from enum import Enum

from app.core.ollama import ollama
from app.core.rag import VectorStore, retrieve_context


class Confidence(str, Enum):
    """Confidence level for a finding."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


@dataclass
class VerificationResult:
    """Result of verifying a claim against sources."""

    claim: str
    confidence: Confidence
    supporting_sources: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)
    notes: str = ""


async def verify_claim(
    claim: str,
    project_id: str,
    top_k: int = 5,
) -> VerificationResult:
    """Verify a claim against the project's knowledge base.

    Args:
        claim: The claim/finding to verify.
        project_id: Project to search in.
        top_k: Number of sources to check.

    Returns:
        VerificationResult with confidence and source evidence.
    """
    # Retrieve relevant documents
    rag_context = await retrieve_context(project_id, claim, top_k=top_k)

    if not rag_context.has_context:
        return VerificationResult(
            claim=claim,
            confidence=Confidence.UNVERIFIED,
            notes="No relevant sources found in the project knowledge base.",
        )

    # Ask the LLM to verify the claim against the sources
    verification_prompt = f"""You are a rigorous UX Research fact-checker. Your job is to verify claims against source documents.

## Claim to Verify
"{claim}"

## Source Documents
{rag_context.context_text}

## Instructions
1. Check if the source documents support, contradict, or are irrelevant to the claim.
2. Rate confidence: HIGH (strong evidence from multiple sources), MEDIUM (some evidence), LOW (weak/indirect evidence), UNVERIFIED (no relevant evidence).
3. List which specific sources support or contradict the claim.

Respond in this exact format:
CONFIDENCE: [HIGH/MEDIUM/LOW/UNVERIFIED]
SUPPORTING: [comma-separated source names, or "none"]
CONTRADICTING: [comma-separated source names, or "none"]
NOTES: [brief explanation of your assessment]"""

    response = await ollama.chat(
        messages=[{"role": "user", "content": verification_prompt}],
        temperature=0.1,
    )

    response_text = response.get("message", {}).get("content", "")

    # Parse the structured response
    confidence = Confidence.UNVERIFIED
    supporting: list[str] = []
    contradicting: list[str] = []
    notes = ""

    for line in response_text.split("\n"):
        line = line.strip()
        if line.startswith("CONFIDENCE:"):
            level = line.split(":", 1)[1].strip().upper()
            try:
                confidence = Confidence(level.lower())
            except ValueError:
                confidence = Confidence.UNVERIFIED
        elif line.startswith("SUPPORTING:"):
            sources = line.split(":", 1)[1].strip()
            if sources.lower() != "none":
                supporting = [s.strip() for s in sources.split(",") if s.strip()]
        elif line.startswith("CONTRADICTING:"):
            sources = line.split(":", 1)[1].strip()
            if sources.lower() != "none":
                contradicting = [s.strip() for s in sources.split(",") if s.strip()]
        elif line.startswith("NOTES:"):
            notes = line.split(":", 1)[1].strip()

    return VerificationResult(
        claim=claim,
        confidence=confidence,
        supporting_sources=supporting,
        contradicting_sources=contradicting,
        notes=notes,
    )


async def check_findings(
    findings: list[str],
    project_id: str,
) -> list[VerificationResult]:
    """Verify multiple findings against the project knowledge base.

    Args:
        findings: List of claims/findings to verify.
        project_id: Project to search in.

    Returns:
        List of verification results.
    """
    results = []
    for finding in findings:
        result = await verify_claim(finding, project_id)
        results.append(result)
    return results


def confidence_to_score(confidence: Confidence) -> float:
    """Convert confidence level to a numerical score (0-1)."""
    mapping = {
        Confidence.HIGH: 0.9,
        Confidence.MEDIUM: 0.6,
        Confidence.LOW: 0.3,
        Confidence.UNVERIFIED: 0.0,
    }
    return mapping.get(confidence, 0.0)
