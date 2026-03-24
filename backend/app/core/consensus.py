"""Consensus Engine — academic-grade inter-rater reliability for LLM outputs.

Implements:
- Fleiss' Kappa (categorical agreement among multiple raters)
- Cosine similarity (semantic agreement via embeddings)
- Composite consensus scoring

References:
- Fleiss, J. L. (1971). Measuring nominal scale agreement among many raters.
- Wang et al. (2025). Mixture-of-Agents. ICLR 2025.
- Li et al. (2025). Self-MoA: Self Mixture-of-Agents.
- Du et al. (2024). Multi-Agent Debate. ICML 2024.
"""

import logging
import math
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """Result of a consensus evaluation."""

    method: str
    agreement_score: float  # 0-1, primary metric
    kappa: float | None  # Fleiss' Kappa (-1 to 1)
    cosine_sim: float | None  # Average pairwise cosine similarity
    confidence: str  # high | medium | low | insufficient
    best_response_idx: int  # Index of the best response
    per_response_scores: list[float]  # Score for each response
    details: dict  # Method-specific details


def fleiss_kappa(ratings_matrix: list[list[int]]) -> float:
    """Compute Fleiss' Kappa for inter-rater reliability.

    Args:
        ratings_matrix: N x k matrix where N = number of items,
                       k = number of categories. Each cell = number
                       of raters who assigned that category to that item.

    Returns:
        Kappa value: 1 = perfect agreement, 0 = chance, <0 = worse than chance.
    """
    if not ratings_matrix or not ratings_matrix[0]:
        return 0.0

    N = len(ratings_matrix)  # number of items
    k = len(ratings_matrix[0])  # number of categories
    n = sum(ratings_matrix[0])  # number of raters (assumed same for all items)

    if n <= 1 or N == 0:
        return 0.0

    # P_i for each item (proportion of pairwise agreement)
    P_i_list = []
    for row in ratings_matrix:
        sum_sq = sum(r * r for r in row)
        P_i = (sum_sq - n) / (n * (n - 1)) if n > 1 else 0
        P_i_list.append(P_i)

    P_bar = sum(P_i_list) / N  # Mean proportion of agreement

    # P_e: expected agreement by chance
    p_j = []
    for j in range(k):
        total = sum(ratings_matrix[i][j] for i in range(N))
        p_j.append(total / (N * n))

    P_e = sum(p * p for p in p_j)

    if abs(1 - P_e) < 1e-10:
        return 1.0 if P_bar >= 1.0 - 1e-10 else 0.0

    kappa = (P_bar - P_e) / (1 - P_e)
    return round(kappa, 4)


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def pairwise_cosine_similarity(embeddings: list[list[float]]) -> float:
    """Average pairwise cosine similarity across all embedding pairs."""
    if len(embeddings) < 2:
        return 1.0

    total = 0.0
    count = 0
    for i in range(len(embeddings)):
        for j in range(i + 1, len(embeddings)):
            total += cosine_similarity(embeddings[i], embeddings[j])
            count += 1

    return total / count if count > 0 else 0.0


def _categorize_response(text: str) -> list[str]:
    """Extract categorical labels from a response for Kappa computation.

    Uses simple keyword extraction for theme categorization.
    """
    text_lower = text.lower()
    categories = []
    # Research-relevant categories
    theme_keywords = {
        "usability": ["usability", "ease of use", "user-friendly", "intuitive"],
        "accessibility": ["accessibility", "wcag", "screen reader", "a11y"],
        "performance": ["performance", "speed", "latency", "fast", "slow"],
        "design": ["design", "layout", "visual", "aesthetic", "ui"],
        "content": ["content", "text", "copy", "information", "clarity"],
        "navigation": ["navigation", "menu", "breadcrumb", "flow"],
        "error": ["error", "bug", "issue", "problem", "fail"],
        "positive": ["good", "excellent", "great", "well", "effective"],
        "negative": ["poor", "bad", "confusing", "difficult", "lacking"],
        "recommendation": ["recommend", "suggest", "improve", "should", "could"],
    }

    for category, keywords in theme_keywords.items():
        if any(kw in text_lower for kw in keywords):
            categories.append(category)

    return categories or ["general"]


def compute_consensus(
    responses: list[str],
    embeddings: list[list[float]] | None = None,
    method: str = "auto",
) -> ConsensusResult:
    """Compute consensus across multiple LLM responses.

    Args:
        responses: List of text responses from different models/runs.
        embeddings: Optional pre-computed embeddings for each response.
        method: Scoring method (auto, kappa, cosine, hybrid).
    """
    n_responses = len(responses)

    if n_responses < 2:
        return ConsensusResult(
            method="single",
            agreement_score=1.0,
            kappa=None,
            cosine_sim=None,
            confidence="insufficient",
            best_response_idx=0,
            per_response_scores=[1.0],
            details={"reason": "Single response — no consensus possible"},
        )

    # Compute Fleiss' Kappa from categorical analysis
    all_categories = set()
    response_categories = []
    for resp in responses:
        cats = _categorize_response(resp)
        response_categories.append(cats)
        all_categories.update(cats)

    cat_list = sorted(all_categories)
    cat_index = {c: i for i, c in enumerate(cat_list)}

    # Build ratings matrix: one item (the task), multiple raters, multiple categories
    # For multi-item Kappa, we treat each category as an item
    ratings_matrix = []
    for cat in cat_list:
        row = [0, 0]  # [present, absent] across raters
        for resp_cats in response_categories:
            if cat in resp_cats:
                row[0] += 1
            else:
                row[1] += 1
        ratings_matrix.append(row)

    kappa = fleiss_kappa(ratings_matrix) if ratings_matrix else 0.0

    # Compute cosine similarity if embeddings provided
    cos_sim = None
    if embeddings and len(embeddings) >= 2:
        cos_sim = pairwise_cosine_similarity(embeddings)

    # Composite agreement score
    if cos_sim is not None:
        agreement = 0.4 * max(kappa, 0) + 0.6 * cos_sim  # Semantic similarity weighted higher
    else:
        agreement = max(kappa, 0)

    # Determine confidence level
    if agreement >= 0.70:
        confidence = "high"
    elif agreement >= 0.50:
        confidence = "medium"
    elif agreement >= 0.30:
        confidence = "low"
    else:
        confidence = "insufficient"

    # Score each response (how well it agrees with others)
    per_scores = []
    for i in range(n_responses):
        if embeddings and len(embeddings) > i:
            # Average cosine similarity with all other responses
            sims = []
            for j in range(n_responses):
                if i != j and j < len(embeddings):
                    sims.append(cosine_similarity(embeddings[i], embeddings[j]))
            per_scores.append(sum(sims) / len(sims) if sims else 0.5)
        else:
            # Category overlap score
            my_cats = set(response_categories[i])
            overlaps = []
            for j in range(n_responses):
                if i != j:
                    other_cats = set(response_categories[j])
                    if my_cats or other_cats:
                        overlaps.append(len(my_cats & other_cats) / len(my_cats | other_cats))
                    else:
                        overlaps.append(0.5)
            per_scores.append(sum(overlaps) / len(overlaps) if overlaps else 0.5)

    best_idx = per_scores.index(max(per_scores)) if per_scores else 0

    return ConsensusResult(
        method=method,
        agreement_score=round(agreement, 4),
        kappa=round(kappa, 4),
        cosine_sim=round(cos_sim, 4) if cos_sim is not None else None,
        confidence=confidence,
        best_response_idx=best_idx,
        per_response_scores=[round(s, 4) for s in per_scores],
        details={
            "n_responses": n_responses,
            "categories_found": cat_list,
            "kappa_interpretation": _interpret_kappa(kappa),
        },
    )


# Tiered confidence thresholds by finding type
CONFIDENCE_THRESHOLDS = {
    "nugget": 0.70,
    "fact": 0.65,
    "insight": 0.55,
    "recommendation": 0.50,
}


def meets_threshold(consensus: ConsensusResult, finding_type: str) -> bool:
    """Check if consensus meets the threshold for a given finding type."""
    threshold = CONFIDENCE_THRESHOLDS.get(finding_type, 0.50)
    return consensus.agreement_score >= threshold


def _interpret_kappa(kappa: float) -> str:
    if kappa >= 0.81:
        return "almost_perfect"
    elif kappa >= 0.61:
        return "substantial"
    elif kappa >= 0.41:
        return "moderate"
    elif kappa >= 0.21:
        return "fair"
    elif kappa >= 0.0:
        return "slight"
    else:
        return "poor"
