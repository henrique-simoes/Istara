"""Research-validity contract and deterministic support logic.

This module does not replace interpretive qualitative coding with deterministic
keyword tagging. It provides the deterministic scaffolding around model coding:
stable evidence units, protected coding prompts, item-by-rater reliability
matrices, promotion gates, route evidence, and graph traceability.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
import json
import re
import uuid

from app.skills.intercoder import cohen_kappa, krippendorff_alpha

DEFAULT_RELIABILITY_THRESHOLD = 0.60

QUALITATIVE_CODING_PROTOCOL = {
    "version": "2026-05-research-validity-v1",
    "method": "inductive_open_coding_with_governed_codebook",
    "principles": [
        "Code evidence units, not keywords or whole final answers.",
        "Assign short interpretive codes to phrases/segments that preserve participant meaning.",
        "Ground every code application in the exact source quote/span.",
        "Use the active codebook definitions, inclusion criteria, exclusion criteria, and examples.",
        "When the codebook is draft, propose new inductive codes with definitions and memos.",
        "When the codebook is frozen, do not invent new codes unless the run is explicitly a revision run.",
        "Treat ambiguity and contradiction as analytic data; memo it instead of smoothing it away.",
        "Keep coders independent until reliability metrics are computed.",
    ],
    "evidence_unit_policy": {
        "unit": "A phrase, speaker turn, observation, survey answer, task episode, ticket, diary entry, or compact passage that can be interpreted without losing source context.",
        "split_guidance": [
            "Preserve speaker turns in interviews and transcripts.",
            "Split long paragraphs into compact sentence groups without changing order.",
            "Keep contradictory or ambiguous statements as codeable evidence, not noise.",
            "Never treat generic retrieval chunks as the source of truth for coding identity.",
        ],
    },
    "open_coding_steps": [
        "Read the evidence unit for participant meaning before applying any existing labels.",
        "Assign one or more concise interpretive codes that capture what the evidence says.",
        "Prefer code labels that name the phenomenon, need, behavior, barrier, mental model, or outcome.",
        "If the active codebook has a matching code, use its code_id and definition.",
        "If the codebook is draft and no code fits, propose a new code label, definition, inclusion criteria, exclusion criteria, and example.",
        "If the codebook is frozen and no code fits, mark the unit as needs_codebook_revision instead of inventing an ungoverned code.",
        "Write a short analytic memo when the evidence is ambiguous, contradictory, deviant, or boundary-setting.",
    ],
    "codebook_requirements": {
        "code_id": "stable kebab-case or governed id",
        "label": "short human-readable label",
        "definition": "what the code means analytically",
        "inclusion_criteria": "when the code should be applied",
        "exclusion_criteria": "nearby cases where the code should not be applied",
        "positive_examples": "examples that clearly qualify",
        "negative_examples": "boundary examples that should be excluded or revised",
        "revision_policy": "frozen codebooks require governed human/project-admin review for changes",
    },
    "ambiguity_policy": {
        "multi_label": "Multi-label coding is allowed when the same evidence unit genuinely supports multiple codes.",
        "primary_code": "A primary_code must be selected for nominal reliability calculations when required.",
        "contradiction": "Contradictions are retained and memoed; do not smooth them into a false consensus.",
        "confidence": "Confidence reflects fit to the codebook and source quote, not model fluency.",
    },
    "required_output_schema": {
        "evidence_unit_id": "stable unit id supplied by Istara",
        "codes": ["code ids or proposed code labels"],
        "primary_code": "single best code when a nominal reliability matrix is required",
        "quote": "exact quoted text used for the code application",
        "confidence": "0.0-1.0 confidence",
        "rationale": "brief qualitative memo explaining why the code applies",
        "ambiguity": "optional disagreement/edge-case note",
        "needs_codebook_revision": "true when a frozen codebook does not fit the evidence",
    },
    "promotion_policy": {
        "default_threshold": DEFAULT_RELIABILITY_THRESHOLD,
        "three_or_more_raters": "Fleiss' Kappa over item-by-rater categorical coding plus companion multi-label checks",
        "two_raters": "Cohen's Kappa and Krippendorff's Alpha over code-by-unit matrices",
        "one_rater": "lower-assurance fallback, never represented as full ensemble reliability",
        "low_agreement": "route to debate/adversarial/human reconciliation before downstream promotion",
        "reports": "reports use accepted/reconciled evidence from approved Done tasks only",
    },
}

RESEARCH_VALIDITY_CONTRACT = {
    "pipeline": [
        "Sources",
        "Evidence Units",
        "Inductive/Open Coding Calibration",
        "Draft Codebook",
        "Human/Governed Codebook Freeze",
        "Independent Multi-Model Coding",
        "Reliability Metrics",
        "Debate/Adversarial/Human Reconciliation",
        "Accepted Code Applications",
        "Nuggets",
        "Facts",
        "Insights",
        "Recommendations",
        "Human-Approved Done Tasks",
        "Reports",
    ],
    "non_negotiables": [
        "Qualitative coding is not keyword tagging.",
        "Reliability metrics are computed on coded evidence-unit matrices.",
        "GraphRAG cannot bypass coding, reliability, review, Done-task, or report gates.",
        "Visible nuggets, facts, insights, or recommendations are provisional until accepted/reconciled coded evidence and approved Done task state make them reportable.",
        "Compression cannot drop protected protocol, codebook, matrix, or gate blocks.",
        "Only accepted/reconciled evidence from approved Done tasks can feed Reports.",
    ],
}

RESEARCH_VALIDITY_TELEMETRY_OPERATIONS = [
    {
        "operation": "evidence_unit.extract",
        "category": "evidence_extraction",
        "required_fields": ["project_id", "evidence_unit_id"],
        "description": "Stable source material was split into project-scoped qualitative evidence units.",
    },
    {
        "operation": "codebook.generate",
        "category": "codebook_governance",
        "required_fields": ["project_id", "codebook_version_id"],
        "description": "A draft codebook or candidate revision was generated for governed review.",
    },
    {
        "operation": "codebook.freeze",
        "category": "codebook_governance",
        "required_fields": ["project_id", "codebook_version_id"],
        "description": "A codebook version became the governed coding contract for later runs.",
    },
    {
        "operation": "codebook.revise",
        "category": "codebook_governance",
        "required_fields": ["project_id", "codebook_version_id"],
        "description": "A governed codebook revision was proposed or applied.",
    },
    {
        "operation": "coding_run.start",
        "category": "coding_reliability",
        "required_fields": ["project_id", "coding_run_id"],
        "description": "Independent qualitative model coding started over evidence units.",
    },
    {
        "operation": "coding_run.model_selected",
        "category": "coding_reliability",
        "required_fields": ["project_id", "coding_run_id", "model_name", "route_id"],
        "description": "Compute Manager selected a distinct model identity for coding.",
    },
    {
        "operation": "coding_run.reliability",
        "category": "coding_reliability",
        "required_fields": ["project_id", "coding_run_id", "reliability_score"],
        "description": "A coded evidence-unit matrix was scored with the configured reliability metric.",
    },
    {
        "operation": "coding_run.low_consensus",
        "category": "coding_reliability",
        "required_fields": ["project_id", "coding_run_id"],
        "description": "A coding run failed promotion and was routed to reconciliation or human review.",
    },
    {
        "operation": "coding_run.complete",
        "category": "coding_reliability",
        "required_fields": ["project_id", "coding_run_id"],
        "description": "Independent coding finished with persisted gate state and route evidence.",
    },
    {
        "operation": "debate.review",
        "category": "review_reconciliation",
        "required_fields": ["project_id", "coding_run_id"],
        "description": "A debate-style review examined coding disagreements with route evidence.",
    },
    {
        "operation": "adversarial.review",
        "category": "review_reconciliation",
        "required_fields": ["project_id", "coding_run_id"],
        "description": "An adversarial review examined disputed code applications and grounding.",
    },
    {
        "operation": "reconciliation_decision.create",
        "category": "review_reconciliation",
        "required_fields": ["project_id", "coding_run_id", "evidence_unit_id"],
        "description": "Human, debate, or adversarial reconciliation resolved a disputed code application.",
    },
    {
        "operation": "human_review.decision",
        "category": "review_reconciliation",
        "required_fields": ["project_id", "task_id"],
        "description": "A reviewer accepted, rejected, revised, or requested more work.",
    },
    {
        "operation": "kanban.status_transition",
        "category": "review_reconciliation",
        "required_fields": ["project_id", "task_id"],
        "description": "A task moved through the review/promotion workflow.",
    },
    {
        "operation": "donor.registered",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id"],
        "description": "A compute donor was registered for project-scoped use.",
    },
    {
        "operation": "donor.visible",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id"],
        "description": "A donor became visible to project compute surfaces.",
    },
    {
        "operation": "donor.reachable",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id"],
        "description": "A donor passed a bounded reachability check.",
    },
    {
        "operation": "donor.ready",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id"],
        "description": "A donor was ready to serve configured model requests.",
    },
    {
        "operation": "donor.selected",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id", "route_id"],
        "description": "Compute Manager selected a donor/model route for a project request.",
    },
    {
        "operation": "donor.served",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id", "route_id"],
        "description": "A donor/model route actually served a request.",
    },
    {
        "operation": "donor.failed",
        "category": "donor_lifecycle",
        "required_fields": ["project_id", "donor_id", "route_id"],
        "description": "A donor/model route failed or was rejected for a project request.",
    },
    {
        "operation": "retrieval.hybrid",
        "category": "retrieval_traceability",
        "required_fields": ["project_id", "retrieval_mode"],
        "description": "Hybrid RAG performed exact evidence lookup with provenance.",
    },
    {
        "operation": "retrieval.graph",
        "category": "retrieval_traceability",
        "required_fields": ["project_id", "retrieval_mode"],
        "description": "Evidence Graph / GraphRAG performed synthesis or dependency traversal.",
    },
    {
        "operation": "retrieval.graph_hybrid",
        "category": "retrieval_traceability",
        "required_fields": ["project_id", "retrieval_mode"],
        "description": "Graph synthesis was backfilled through Hybrid RAG evidence handles.",
    },
    {
        "operation": "evidence_graph.traceability",
        "category": "retrieval_traceability",
        "required_fields": ["project_id", "retrieval_mode"],
        "description": "A read-only traceability route joined graph and exact-evidence dependencies.",
    },
    {
        "operation": "prompt_rag.context",
        "category": "retrieval_traceability",
        "required_fields": ["project_id", "retrieval_mode"],
        "description": "Prompt-RAG supplied optional context without owning mandatory methodology.",
    },
    {
        "operation": "compression.protected_block",
        "category": "context_safety",
        "required_fields": ["project_id"],
        "description": "Compression preserved protected protocol, codebook, matrix, gate, or graph blocks.",
    },
    {
        "operation": "finding.promotion",
        "category": "promotion_gate",
        "required_fields": ["project_id", "task_id"],
        "description": "Accepted/reconciled coded evidence was promoted into research artifacts.",
    },
    {
        "operation": "report.promotion_gate",
        "category": "promotion_gate",
        "required_fields": ["project_id", "task_id"],
        "description": "Report generation checked Done task and accepted-evidence gates.",
    },
    {
        "operation": "autoresearch.validity_update",
        "category": "governed_learning",
        "required_fields": ["project_id"],
        "description": "Autoresearch adjusted plans based on research-validity telemetry without bypassing gates.",
    },
    {
        "operation": "self_evolution.proposal",
        "category": "governed_learning",
        "required_fields": ["project_id"],
        "description": "Self-evolution proposed a governed improvement based on validity evidence.",
    },
    {
        "operation": "reasoning_bank.lesson",
        "category": "governed_learning",
        "required_fields": ["project_id"],
        "description": "ReasoningBank stored a process lesson that is not report evidence.",
    },
    {
        "operation": "memento_skill.health",
        "category": "governed_learning",
        "required_fields": ["project_id", "skill_name"],
        "description": "Skill health incorporated evidence validity and reliability signals.",
    },
    {
        "operation": "meta_hyperagent.proposal",
        "category": "governed_learning",
        "required_fields": ["project_id"],
        "description": "Meta-Hyperagent proposed reviewable improvements to orchestration quality.",
    },
]

PROTECTED_RESEARCH_TAGS = [
    "qualitative_coding_protocol",
    "codebook",
    "evidence_units",
    "coding_matrix",
    "reliability_policy",
    "promotion_gate",
    "route_evidence",
    "evidence_graph",
]


@dataclass(slots=True)
class EvidenceUnitDraft:
    id: str
    stable_id: str
    unit_index: int
    source_text: str
    source_location: str
    start_offset: int | None = None
    end_offset: int | None = None
    speaker: str = ""
    participant_id: str = ""
    method: str = ""
    phase: str = ""
    metadata: dict = field(default_factory=dict)


def _stable_uuid(*parts: str) -> str:
    digest = sha256("::".join(parts).encode("utf-8")).hexdigest()
    return str(uuid.UUID(digest[:32]))


def _split_candidate_units(text: str) -> list[tuple[str, int, int, str]]:
    """Split source text into stable qualitative evidence units.

    The split is deterministic and conservative: speaker turns, paragraphs, and
    compact sentence groups become units. The interpretive coding itself remains
    a model/human task downstream.
    """
    candidates: list[tuple[str, int, int, str]] = []
    if not text:
        return candidates

    speaker_turn = re.compile(r"(?m)^(?P<speaker>[A-Z][A-Za-z0-9 _.-]{0,60}):\s*(?P<body>.+)$")
    consumed: list[tuple[int, int]] = []
    for match in speaker_turn.finditer(text):
        body = match.group("body").strip()
        if body:
            candidates.append((body, match.start("body"), match.end("body"), match.group("speaker")))
            consumed.append((match.start(), match.end()))

    paragraphs: list[tuple[str, int, int]] = []
    for match in re.finditer(r"\S(?:.*?)(?=\n\s*\n|\Z)", text, re.DOTALL):
        start, end = match.span()
        if any(start < c_end and end > c_start for c_start, c_end in consumed):
            continue
        paragraph = re.sub(r"\s+", " ", match.group().strip())
        if paragraph:
            paragraphs.append((paragraph, start, end))

    for paragraph, start, end in paragraphs:
        if len(paragraph) <= 420:
            candidates.append((paragraph, start, end, ""))
            continue
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        buffer: list[str] = []
        buffer_start = start
        cursor = start
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_start = text.find(sentence, cursor, end)
            if sentence_start == -1:
                sentence_start = cursor
            if not buffer:
                buffer_start = sentence_start
            buffer.append(sentence)
            cursor = sentence_start + len(sentence)
            if sum(len(s) for s in buffer) >= 260:
                unit = " ".join(buffer)
                candidates.append((unit, buffer_start, cursor, ""))
                buffer = []
        if buffer:
            unit = " ".join(buffer)
            candidates.append((unit, buffer_start, end, ""))

    deduped: list[tuple[str, int, int, str]] = []
    seen: set[str] = set()
    for candidate in sorted(candidates, key=lambda item: (item[1], item[2])):
        normalized = re.sub(r"\s+", " ", candidate[0]).strip()
        key = f"{candidate[1]}:{candidate[2]}:{normalized[:80]}"
        if normalized and key not in seen:
            seen.add(key)
            deduped.append((normalized, candidate[1], candidate[2], candidate[3]))
    return deduped


def segment_evidence_units(
    *,
    project_id: str,
    source_text: str,
    source_id: str,
    source_location: str = "",
    participant_id: str = "",
    method: str = "",
    phase: str = "",
) -> list[EvidenceUnitDraft]:
    """Create stable evidence-unit drafts from source material."""
    units: list[EvidenceUnitDraft] = []
    for index, (unit_text, start, end, speaker) in enumerate(_split_candidate_units(source_text), 1):
        stable_id = f"{source_id}#EU-{index:04d}"
        units.append(
            EvidenceUnitDraft(
                id=_stable_uuid(project_id, source_id, str(index), unit_text),
                stable_id=stable_id,
                unit_index=index,
                source_text=unit_text,
                source_location=source_location or stable_id,
                start_offset=start,
                end_offset=end,
                speaker=speaker,
                participant_id=participant_id,
                method=method,
                phase=phase,
                metadata={"segmentation": "speaker_turn_paragraph_sentence_group"},
            )
        )
    return units


def protected_block(tag: str, payload) -> str:
    """Serialize a protected research-validity block."""
    if tag not in PROTECTED_RESEARCH_TAGS:
        raise ValueError(f"Unknown protected research tag: {tag}")
    text = payload if isinstance(payload, str) else json.dumps(payload, indent=2, sort_keys=True)
    return f"<{tag}>\n{text}\n</{tag}>"


def build_qualitative_coding_prompt(
    *,
    evidence_units: list[dict],
    codebook: dict | list | None,
    project_policy: dict | None = None,
) -> str:
    """Build the mandatory prompt block for independent model coders."""
    policy = {
        "default_threshold": DEFAULT_RELIABILITY_THRESHOLD,
        "low_agreement_action": "route_to_reconciliation_or_human_review",
        "report_gate": "accepted_evidence_and_approved_done_tasks_only",
    }
    if project_policy:
        policy.update(project_policy)

    return "\n\n".join(
        [
            protected_block("qualitative_coding_protocol", QUALITATIVE_CODING_PROTOCOL),
            protected_block("codebook", codebook or {"status": "draft", "codes": []}),
            protected_block("evidence_units", evidence_units),
            protected_block("reliability_policy", policy),
        ]
    )


def normalize_coder_applications(applications: list[dict]) -> dict[str, dict[str, set[str]]]:
    """Return coder_id -> evidence_unit_id -> code set."""
    coder_units: dict[str, dict[str, set[str]]] = {}
    for app in applications:
        coder_id = str(app.get("coder_id") or app.get("model_name") or app.get("coder") or "").strip()
        evidence_unit_id = str(app.get("evidence_unit_id") or app.get("unit_id") or "").strip()
        if not coder_id or not evidence_unit_id:
            continue
        codes = app.get("codes")
        if codes is None:
            codes = [app.get("code_id") or app.get("primary_code")]
        normalized_codes = {str(code).strip() for code in codes if str(code or "").strip()}
        coder_units.setdefault(coder_id, {}).setdefault(evidence_unit_id, set()).update(normalized_codes)
    return coder_units


def distinct_model_identities(applications: list[dict]) -> set[str]:
    """Return model identities that count as independent model coders.

    A distinct *configured endpoint identity* is a distinct independent coder,
    even when several endpoints advertise the same model name. W7: Pi catalog
    rows are endpoint identities, so three endpoints serving one model are three
    raters and must not collapse to one — the exact endpoint identity is
    preserved through the reliability gate. The ephemeral route/call id is never
    a distinctness axis on its own, so the same model on the same endpoint
    invoked twice stays a single rater and fabricated diversity stays blocked.
    """
    identities: set[str] = set()
    for app in applications:
        model_name = str(app.get("model_name") or app.get("model") or "").strip()
        endpoint_id = str(
            app.get("endpoint_id")
            or app.get("donor_id")
            or app.get("node_id")
            or ""
        ).strip()
        route_id = str(app.get("route_id") or app.get("route") or "").strip()
        coder_id = str(app.get("coder_id") or app.get("coder") or "").strip()
        identity = model_name or coder_id
        if not identity and not endpoint_id:
            continue
        # A distinct configured endpoint identity keeps same-model Pi endpoints
        # as separate raters; a bare repeated model name (no endpoint) still
        # collapses to one identity.
        if endpoint_id:
            identity = f"{identity}@{endpoint_id}" if identity else endpoint_id
        elif route_id and not model_name:
            # Only when there is no endpoint identity to key on does a route id
            # disambiguate, and never for an otherwise-identical model — a call
            # counter must not manufacture independent raters.
            identity = f"{identity}@{route_id}"
        identities.add(identity)
    return identities


def _all_codes(coder_units: dict[str, dict[str, set[str]]]) -> list[str]:
    codes: set[str] = set()
    for unit_map in coder_units.values():
        for code_set in unit_map.values():
            codes.update(code_set)
    return sorted(codes)


def build_binary_coding_matrix(applications: list[dict]) -> dict:
    """Build a reconstructable evidence-unit by rater matrix."""
    coder_units = normalize_coder_applications(applications)
    coders = sorted(coder_units)
    units = sorted({unit_id for unit_map in coder_units.values() for unit_id in unit_map})
    codes = _all_codes(coder_units)
    matrix = {
        unit_id: {
            coder_id: sorted(coder_units.get(coder_id, {}).get(unit_id, set()))
            for coder_id in coders
        }
        for unit_id in units
    }
    return {"coders": coders, "evidence_units": units, "codes": codes, "matrix": matrix}


def item_level_promotion_statuses(matrix: dict, run_promotion_status: str) -> dict[str, str]:
    """Return per-evidence-unit promotion status from coder agreement.

    A passing run-level score proves the coding pass is reliable enough to use,
    but it must not automatically promote each item. Individual evidence units
    still need exact coder agreement or reconciliation before they become
    reportable.
    """
    coders = matrix.get("coders", [])
    rows = matrix.get("matrix", {})
    statuses: dict[str, str] = {}
    for unit_id in matrix.get("evidence_units", []):
        coder_code_sets = [tuple(rows.get(unit_id, {}).get(coder_id, [])) for coder_id in coders]
        has_all_coders = bool(coders) and all(code_set for code_set in coder_code_sets)
        exact_agreement = has_all_coders and len(set(coder_code_sets)) == 1
        if run_promotion_status == "accepted" and exact_agreement:
            statuses[unit_id] = "accepted"
        elif run_promotion_status == "accepted":
            statuses[unit_id] = "needs_reconciliation"
        else:
            statuses[unit_id] = run_promotion_status or "blocked"
    return statuses


def fleiss_kappa_from_matrix(matrix: dict) -> dict:
    """Compute Fleiss' Kappa over item-by-rater categorical code-set labels."""
    coders = matrix.get("coders", [])
    units = matrix.get("evidence_units", [])
    rows = matrix.get("matrix", {})
    if len(coders) < 3 or not units:
        return {
            "kappa": None,
            "method": "fleiss_kappa",
            "status": "not_applicable",
            "reason": "Fleiss' Kappa requires at least three raters and one evidence unit.",
        }

    categories: list[str] = []
    counts_by_unit: list[dict[str, int]] = []
    for unit_id in units:
        counts: dict[str, int] = {}
        for coder_id in coders:
            code_set = rows.get(unit_id, {}).get(coder_id, [])
            category = "|".join(sorted(code_set)) if code_set else "__none__"
            counts[category] = counts.get(category, 0) + 1
            if category not in categories:
                categories.append(category)
        counts_by_unit.append(counts)

    n_items = len(counts_by_unit)
    n_raters = len(coders)
    if n_raters < 2:
        return {"kappa": 0.0, "method": "fleiss_kappa", "status": "invalid"}

    p_i_values = []
    for counts in counts_by_unit:
        p_i = (sum(count * count for count in counts.values()) - n_raters) / (n_raters * (n_raters - 1))
        p_i_values.append(p_i)
    p_bar = sum(p_i_values) / n_items

    p_j: dict[str, float] = {}
    for category in categories:
        p_j[category] = sum(counts.get(category, 0) for counts in counts_by_unit) / (n_items * n_raters)
    p_e = sum(value * value for value in p_j.values())

    if p_e == 1.0:
        kappa = 1.0 if p_bar == 1.0 else 0.0
    else:
        kappa = (p_bar - p_e) / (1 - p_e)

    return {
        "kappa": round(kappa, 3),
        "method": "fleiss_kappa",
        "status": "computed",
        "n_items": n_items,
        "n_raters": n_raters,
        "categories": categories,
        "observed_agreement": round(p_bar, 3),
        "expected_agreement": round(p_e, 3),
    }


def evaluate_reliability_gate(
    applications: list[dict],
    *,
    threshold: float = DEFAULT_RELIABILITY_THRESHOLD,
) -> dict:
    """Evaluate the corrected reliability policy for coded evidence units."""
    matrix = build_binary_coding_matrix(applications)
    coders = matrix["coders"]
    coder_item_lists: list[list[list[str]]] = []
    for coder_id in coders:
        coder_item_lists.append([matrix["matrix"][unit_id].get(coder_id, []) for unit_id in matrix["evidence_units"]])

    result: dict = {
        "threshold": threshold,
        "rater_count": len(coders),
        "distinct_model_count": len(distinct_model_identities(applications)) or len(coders),
        "matrix": matrix,
        "promotion_status": "blocked",
        "fallback_reason": "",
        "low_agreement_codes": [],
        "method": "",
    }

    if len(coders) >= 2 and result["distinct_model_count"] < len(coders):
        result.update(
            {
                "method": "invalid_independence",
                "kappa": None,
                "alpha": None,
                "promotion_status": "needs_reconciliation",
                "fallback_reason": "Independent coding reused a model identity as if it were a distinct coder.",
            }
        )
        return result

    if len(coders) >= 3:
        fleiss = fleiss_kappa_from_matrix(matrix)
        alpha = krippendorff_alpha(coder_item_lists, matrix["codes"])
        score = fleiss.get("kappa")
        result.update(
            {
                "method": "fleiss_kappa_with_krippendorff_alpha_companion",
                "kappa": score,
                "alpha": alpha.get("alpha"),
                "details": {"fleiss": fleiss, "krippendorff_alpha": alpha},
                "low_agreement_codes": alpha.get("unreliable_codes", []),
            }
        )
        result["promotion_status"] = "accepted" if score is not None and score >= threshold else "needs_reconciliation"
    elif len(coders) == 2:
        cohen = cohen_kappa(coder_item_lists[0], coder_item_lists[1], matrix["codes"])
        alpha = krippendorff_alpha(coder_item_lists, matrix["codes"])
        score = cohen.get("kappa")
        result.update(
            {
                "method": "cohen_kappa_with_krippendorff_alpha_companion",
                "kappa": score,
                "alpha": alpha.get("alpha"),
                "details": {"cohen_kappa": cohen, "krippendorff_alpha": alpha},
                "low_agreement_codes": cohen.get("low_agreement_codes", []),
            }
        )
        result["promotion_status"] = "accepted" if score is not None and score >= threshold else "needs_reconciliation"
    elif len(coders) == 1:
        result.update(
            {
                "method": "single_coder_lower_assurance",
                "kappa": None,
                "alpha": None,
                "promotion_status": "needs_human_review",
                "fallback_reason": "Only one coder/model is available; this is not full ensemble reliability.",
            }
        )
    else:
        result.update(
            {
                "method": "no_coders",
                "kappa": None,
                "alpha": None,
                "promotion_status": "blocked",
                "fallback_reason": "No independent coding applications were supplied.",
            }
        )
    item_statuses = item_level_promotion_statuses(matrix, result["promotion_status"])
    result["item_promotion_statuses"] = item_statuses
    result["accepted_evidence_unit_ids"] = [
        unit_id for unit_id, status in item_statuses.items() if status == "accepted"
    ]
    result["reconciliation_evidence_unit_ids"] = [
        unit_id for unit_id, status in item_statuses.items() if status != "accepted"
    ]
    return result


def graph_edge_metadata(
    *,
    retrieval_mode: str = "hybrid",
    review_status: str = "",
    reliability_status: str = "",
    route_evidence: dict | None = None,
) -> dict:
    return {
        "retrieval_mode": retrieval_mode,
        "review_status": review_status,
        "reliability_status": reliability_status,
        "route_evidence": route_evidence or {},
        "graph_policy": "graph_results_must_backfill_exact_hybrid_evidence_before_promotion",
    }


def retrieval_metadata_for_unit(unit: EvidenceUnitDraft | dict) -> dict:
    """Expose evidence-unit provenance to RAG without storing private content in telemetry."""
    data = unit if isinstance(unit, dict) else asdict(unit)
    return {
        "evidence_unit_id": data.get("id"),
        "stable_id": data.get("stable_id"),
        "source_location": data.get("source_location"),
        "start_offset": data.get("start_offset"),
        "end_offset": data.get("end_offset"),
        "method": data.get("method", ""),
        "phase": data.get("phase", ""),
        "retrieval_role": "exact_evidence",
    }


def telemetry_operation_names() -> list[str]:
    return [row["operation"] for row in RESEARCH_VALIDITY_TELEMETRY_OPERATIONS]


def research_validity_telemetry_contract() -> dict:
    """Return the content-free telemetry taxonomy for the corrected workflow."""
    categories: dict[str, list[str]] = {}
    for row in RESEARCH_VALIDITY_TELEMETRY_OPERATIONS:
        categories.setdefault(row["category"], []).append(row["operation"])
    return {
        "content_policy": "content_free_handles_only",
        "operations": RESEARCH_VALIDITY_TELEMETRY_OPERATIONS,
        "categories": categories,
        "protected_fields": [
            "prompt",
            "response",
            "source_text",
            "quote",
            "file_content",
            "url",
            "connection_string",
            "token",
        ],
    }
