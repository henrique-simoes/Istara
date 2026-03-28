"""Laws of UX Knowledge Service — query, match, enrich, and score.

Based on the 30 Laws of UX by Jon Yablonski (lawsofux.com, CC BY-SA 4.0).
Provides pure-Python functions with zero LLM dependency.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

LAWS_FILE = Path(__file__).parent.parent / "knowledge" / "laws_of_ux.json"


class LawsOfUXService:
    """Query, match, and score UX laws against findings."""

    def __init__(self):
        self._laws: dict[str, dict] = {}  # id -> law
        self._keyword_index: dict[str, set[str]] = {}  # law_id -> set of keywords
        self._heuristic_map: dict[str, list[str]] = {}  # heuristic_id -> [law_ids]
        self._loaded = False
        self._load()

    def _load(self):
        try:
            if not LAWS_FILE.exists():
                logger.warning("laws_of_ux.json not found at %s", LAWS_FILE)
                return
            data = json.loads(LAWS_FILE.read_text())
            for law in data.get("laws", []):
                self._laws[law["id"]] = law
                self._keyword_index[law["id"]] = set(
                    k.lower() for k in law.get("detection_keywords", [])
                )
                for h in law.get("related_nielsen_heuristics", []):
                    self._heuristic_map.setdefault(h, []).append(law["id"])
            self._loaded = True
            logger.info("Loaded %d Laws of UX", len(self._laws))
        except Exception:
            logger.exception("Failed to load laws_of_ux.json")

    def get_all(self) -> list[dict]:
        """Return all loaded laws."""
        return list(self._laws.values())

    def get_by_id(self, law_id: str) -> dict | None:
        """Return a single law by its ID, or None."""
        return self._laws.get(law_id)

    def get_by_category(self, category: str) -> list[dict]:
        """Return all laws in a given category."""
        return [l for l in self._laws.values() if l.get("category") == category]

    def get_related_to_heuristic(self, heuristic_id: str) -> list[dict]:
        """Return all laws related to a Nielsen heuristic (e.g. H4)."""
        law_ids = self._heuristic_map.get(heuristic_id, [])
        return [self._laws[lid] for lid in law_ids if lid in self._laws]

    def match_text(self, text: str, top_k: int = 3) -> list[tuple[str, float]]:
        """Keyword-match text against law detection_keywords.

        Uses Jaccard-like overlap scoring (same pattern as prompt_rag.py).
        Returns [(law_id, score)] sorted by score descending.
        """
        text_tokens = set(re.findall(r'\b\w{3,}\b', text.lower()))
        if not text_tokens:
            return []

        scores = []
        for law_id, keywords in self._keyword_index.items():
            overlap = text_tokens & keywords
            if not overlap:
                continue
            # Jaccard-ish similarity
            score = len(overlap) / (len(text_tokens) + len(keywords) - len(overlap))
            # Boost for multiple keyword matches (compound evidence)
            if len(overlap) >= 2:
                score *= 1.3
            scores.append((law_id, min(score, 1.0)))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def enrich_tags(
        self, existing_tags: list[str], text: str, threshold: float = 0.08
    ) -> list[str]:
        """Append matching ux-law:{id} tags to existing tags.

        Does NOT replace existing tags. Uses 'ux-law:' prefix to avoid collisions.
        """
        if not self._loaded or not text:
            return existing_tags

        matches = self.match_text(text, top_k=5)
        law_tags = [
            f"ux-law:{law_id}" for law_id, score in matches if score >= threshold
        ]

        # Merge without duplicates
        existing_set = set(existing_tags)
        for tag in law_tags:
            if tag not in existing_set:
                existing_tags.append(tag)
        return existing_tags

    def compute_compliance_profile(self, nuggets: list[dict]) -> dict:
        """Aggregate nugget tags into per-law compliance scores.

        A law with zero violations scores 100.
        Score degrades proportionally to violation count.
        """
        law_violations: dict[str, list[str]] = {lid: [] for lid in self._laws}

        for nugget in nuggets:
            tags = nugget.get("tags", [])
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except Exception:
                    tags = []
            for tag in tags:
                if tag.startswith("ux-law:"):
                    law_id = tag.removeprefix("ux-law:")
                    if law_id in law_violations:
                        law_violations[law_id].append(nugget.get("id", ""))

        by_law = []
        category_scores: dict[str, list[float]] = {}

        for law_id, violations in law_violations.items():
            law = self._laws[law_id]
            count = len(violations)
            # Score: 100 - (violations * 15), min 0
            score = max(0, 100 - count * 15)
            by_law.append(
                {
                    "law_id": law_id,
                    "law_name": law["name"],
                    "category": law["category"],
                    "score": score,
                    "violation_count": count,
                    "finding_ids": violations,
                }
            )
            cat = law["category"]
            category_scores.setdefault(cat, []).append(score)

        by_category = {}
        for cat, scores in category_scores.items():
            by_category[cat] = {
                "score": round(sum(scores) / len(scores)) if scores else 100,
                "laws_evaluated": len(scores),
                "violations": sum(1 for s in scores if s < 100),
            }

        overall = (
            round(sum(l["score"] for l in by_law) / len(by_law)) if by_law else 100
        )

        return {
            "overall_score": overall,
            "by_category": by_category,
            "by_law": sorted(by_law, key=lambda x: x["score"]),
        }

    def get_radar_chart_data(self, compliance: dict) -> dict:
        """Transform compliance to radar chart format."""
        by_law = compliance.get("by_law", [])
        return {
            "categories": list(compliance.get("by_category", {}).keys()),
            "category_scores": [
                v["score"] for v in compliance.get("by_category", {}).values()
            ],
            "detailed_axes": [
                {"axis": l["law_name"], "value": l["score"]} for l in by_law
            ],
        }


# Singleton
laws_service = LawsOfUXService()
