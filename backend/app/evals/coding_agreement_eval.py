"""C2/C3: why do three model coders disagree, and does a codebook fix it? (DEC-3)

Professional-readiness review (2026-09-26). Units are planted Harbor Ledger quotes, so each unit's
theme is known by construction (span-graded truth). The same units are coded by the product's own
independent coding run (``run_independent_coding_run``, three pi coders) in two fresh projects:

  arm A  no codebook (today's default: open coding)
  arm B  the Harbor codebook below: ten codes with definitions and inclusion/exclusion criteria

Reported per arm: Fleiss kappa and Krippendorff alpha on each coder's normalised primary code, the
same on exact label sets (what ``main`` compared before D-8), the product gate's own kappa, and in
arm B each coder's accuracy against the planted theme. Paired differences use units as pairs
(bootstrap over units), Holm over kappa and alpha. DEC-3 attributes the cause.

Run inside the backend container, which owns the database:

    python -m app.evals.coding_agreement_eval --qrels /app/data/eval/thematic.json \\
        --per-theme 5 --out /app/data/eval/c2.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import uuid
from collections import Counter
from datetime import UTC, datetime

from app.core.research_validity import normalize_code_label

SEED = 20260927

# Written from the corpus generator's theme titles before any coder output was seen (DEC-3).
CODEBOOK = [
    {
        "code": "invoice_chasing",
        "theme": "T1",
        "definition": "Time and effort spent working out who owes money and chasing late payers.",
        "include": "Overdue invoices, reminders, receivables, matching payments to clients.",
        "exclude": "Receipts for the business's own spending (receipt_capture).",
    },
    {
        "code": "receipt_capture",
        "theme": "T2",
        "definition": "Receipts for purchases get lost or are never recorded at the point of sale.",
        "include": "Paper receipts, photos, shoeboxes, expenses recorded late or never.",
        "exclude": "Money owed by clients (invoice_chasing).",
    },
    {
        "code": "approval_bottleneck",
        "theme": "T3",
        "definition": "Approvals wait on one person who is absent, so work stalls.",
        "include": "Sign-off chains, a single approver on leave, delegation gaps.",
        "exclude": "Payroll timing (payroll_cash_timing).",
    },
    {
        "code": "bank_feed_trust",
        "theme": "T4",
        "definition": "Automatic matching of bank-feed transactions: owners like it, accountants "
        "distrust it.",
        "include": "Auto-match accuracy, reviewing or undoing matches, trust in reconciliation.",
        "exclude": "Manual receivables chasing (invoice_chasing).",
    },
    {
        "code": "payroll_cash_timing",
        "theme": "T5",
        "definition": "Payroll dates do not line up with when cash actually arrives.",
        "include": "Paying staff before customers pay, cash-flow gaps around payday.",
        "exclude": "Approvals waiting on a person (approval_bottleneck).",
    },
    {
        "code": "translation_meaning",
        "theme": "T6",
        "definition": "Spanish statements and screens translate words but lose the meaning.",
        "include": "Mistranslated financial terms; Spanish speakers misreading statements.",
        "exclude": "Accessibility barriers unrelated to language.",
    },
    {
        "code": "branch_handoff",
        "theme": "T7",
        "definition": "Context is lost when a customer moves between channels or branch staff.",
        "include": "Repeating the story at the counter; notes not carried between staff.",
        "exclude": "Fraud alert volume (fraud_alert_volume).",
    },
    {
        "code": "fraud_alert_volume",
        "theme": "T8",
        "definition": "Fraud alerts: operations want more of them, owners feel spammed.",
        "include": "False positives, alert fatigue, blocked payments, too many or too few alerts.",
        "exclude": "Mobile deposit limits (mobile_deposit_limits).",
    },
    {
        "code": "accountant_collaboration",
        "theme": "T9",
        "definition": "Working with the accountant runs on screenshots and back-and-forth.",
        "include": "Sending screenshots or exports, questions by email, no shared workspace.",
        "exclude": "Trust in auto-matching itself (bank_feed_trust).",
    },
    {
        "code": "mobile_deposit_limits",
        "theme": "T10",
        "definition": "Mobile cheque-deposit limits surprise businesses as they grow.",
        "include": "Deposit caps, rejected mobile deposits, having to visit a branch to deposit.",
        "exclude": "Fraud alerts (fraud_alert_volume).",
    },
]
THEME_CODE = {entry["theme"]: normalize_code_label(entry["code"]) for entry in CODEBOOK}


def select_units(qrels: dict, per_theme: int, seed: int = SEED) -> list[tuple[str, str]]:
    """``per_theme`` planted quotes of each theme, fixed by the seed: (theme, quote)."""
    by_theme: dict[str, set[str]] = {}
    for question in qrels["questions"]:
        by_theme.setdefault(question["theme"], set()).update(question["targets"])
    rng = random.Random(seed)
    chosen = []
    for theme in sorted(by_theme, key=lambda t: int(t[1:])):
        quotes = sorted(by_theme[theme])
        chosen += [(theme, q) for q in rng.sample(quotes, min(per_theme, len(quotes)))]
    rng.shuffle(chosen)
    return chosen


def fleiss_kappa(ratings: list[list[str]]) -> float | None:
    """Nominal Fleiss kappa; ``ratings[i]`` holds every coder's category for unit i."""
    rows = [r for r in ratings if len(r) >= 2]
    if not rows or len({len(r) for r in rows}) != 1:
        return None
    n = len(rows[0])
    totals: Counter = Counter()
    p_bar = 0.0
    for row in rows:
        counts = Counter(row)
        totals.update(counts)
        p_bar += (sum(c * c for c in counts.values()) - n) / (n * (n - 1))
    p_bar /= len(rows)
    grand = len(rows) * n
    p_e = sum((c / grand) ** 2 for c in totals.values())
    if p_e >= 1.0:
        return 1.0 if p_bar >= 1.0 else None
    return (p_bar - p_e) / (1 - p_e)


def krippendorff_alpha(ratings: list[list[str]]) -> float | None:
    """Nominal Krippendorff alpha from pairable values (units with at least two ratings)."""
    rows = [r for r in ratings if len(r) >= 2]
    values: Counter = Counter()
    disagree_observed = 0.0
    for row in rows:
        m = len(row)
        counts = Counter(row)
        values.update(counts)
        pairs_disagree = m * m - sum(c * c for c in counts.values())
        disagree_observed += pairs_disagree / (m - 1)
    total = sum(values.values())
    if total <= 1:
        return None
    disagree_expected = (total * total - sum(c * c for c in values.values())) / (total - 1)
    if disagree_expected == 0:
        return 1.0
    return 1 - disagree_observed / disagree_expected


def unit_agreement(row: list[str]) -> float:
    """Share of coder pairs on one unit that chose the same category."""
    m = len(row)
    if m < 2:
        return 0.0
    counts = Counter(row)
    return sum(c * (c - 1) for c in counts.values()) / (m * (m - 1))


def paired_bootstrap(
    a: list[list[str]], b: list[list[str]], metric, *, resamples: int = 5000, seed: int = SEED
) -> dict:
    """metric(b) - metric(a) with units resampled jointly; two-sided p that the difference is 0."""
    rng = random.Random(seed)
    n = len(a)
    observed = (metric(b) or 0.0) - (metric(a) or 0.0)
    diffs = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append((metric([b[i] for i in idx]) or 0.0) - (metric([a[i] for i in idx]) or 0.0))
    diffs.sort()
    below = sum(1 for d in diffs if d <= 0) / resamples
    above = sum(1 for d in diffs if d >= 0) / resamples
    return {
        "difference": round(observed, 4),
        "ci95": [round(diffs[int(0.025 * resamples)], 4), round(diffs[int(0.975 * resamples)], 4)],
        "p": round(min(1.0, 2 * min(below, above)), 4),
    }


def _ratings(per_unit: dict[str, dict[str, str]], unit_ids: list[str], coders: list[str]):
    """Rows of categories for units every coder rated (complete cases)."""
    return [
        [per_unit[u][c] for c in coders]
        for u in unit_ids
        if u in per_unit and all(c in per_unit[u] for c in coders)
    ]


async def _run_arm(label: str, units: list[tuple[str, str]], with_codebook: bool) -> dict:
    from sqlalchemy import select

    from app.models.code_application import CodeApplication
    from app.models.codebook_version import CodebookVersion
    from app.models.database import async_session
    from app.models.project import Project
    from app.models.research_validity import CodingRun, EvidenceUnit
    from app.services.research_validity_service import run_independent_coding_run

    project_id = str(uuid.uuid4())
    unit_ids: list[str] = []
    truth: dict[str, str] = {}
    async with async_session() as db:
        db.add(Project(id=project_id, name=f"C2 coding agreement ({label})"))
        if with_codebook:
            db.add(
                CodebookVersion(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    version="1.0.0",
                    codes_json=json.dumps(
                        [{k: v for k, v in e.items() if k != "theme"} for e in CODEBOOK]
                    ),
                    change_log="C2 Harbor codebook (DEC-3)",
                    created_by="c2-eval",
                    methodology="codebook_ta",
                )
            )
        for index, (theme, quote) in enumerate(units):
            unit_id = str(uuid.uuid4())
            db.add(
                EvidenceUnit(
                    id=unit_id,
                    project_id=project_id,
                    source_id=f"c2:{label}",
                    stable_id=f"c2-{label}-{index:03d}",
                    unit_index=index,
                    unit_type="source_span",
                    source_type="interview_transcript",
                    method="c2_eval",
                    source_text=quote,
                    source_location=f"harbor#unit-{index:03d}",
                    start_offset=0,
                    end_offset=len(quote),
                )
            )
            unit_ids.append(unit_id)
            truth[unit_id] = theme
        await db.commit()
        started = datetime.now(UTC)
        run = await run_independent_coding_run(
            db,
            project_id=project_id,
            evidence_unit_ids=unit_ids,
            max_coders=3,
            limit=len(unit_ids),
            created_by="c2-eval",
        )
        coding_run = await db.get(CodingRun, run["id"])
        matrix = json.loads(coding_run.matrix_json or "{}")
        rows = (
            (
                await db.execute(
                    select(CodeApplication).where(CodeApplication.coding_run_id == run["id"])
                )
            )
            .scalars()
            .all()
        )
    primary: dict[str, dict[str, str]] = {}
    for unit_id, per_coder in (matrix.get("matrix") or {}).items():
        for coder, codes in per_coder.items():
            if codes:
                primary.setdefault(unit_id, {})[coder] = "|".join(sorted(codes))
    exact_sets: dict[str, dict[str, set[str]]] = {}
    models: dict[str, str] = {}
    for row in rows:
        exact_sets.setdefault(row.evidence_unit_id, {}).setdefault(row.coder_id, set()).add(
            row.code_id
        )
        models[row.coder_id] = row.model_name
    exact = {u: {c: "|".join(sorted(s)) for c, s in per.items()} for u, per in exact_sets.items()}
    coders = sorted(models)
    primary_rows = _ratings(primary, unit_ids, coders)
    exact_rows = _ratings(exact, unit_ids, coders)
    accuracy = {}
    for coder in coders:
        rated = [u for u in unit_ids if coder in primary.get(u, {})]
        right = sum(1 for u in rated if primary[u][coder] == THEME_CODE[truth[u]])
        accuracy[models[coder]] = {
            "rated": len(rated),
            "correct": right,
            "accuracy": round(right / len(unit_ids), 4) if unit_ids else None,
        }
    return {
        "arm": label,
        "codebook": with_codebook,
        "project_id": project_id,
        "coding_run_id": run["id"],
        "started": started.isoformat(),
        "units": len(unit_ids),
        "coders": [models[c] for c in coders],
        "complete_units": len(primary_rows),
        "gate": {
            "kappa": coding_run.kappa,
            "alpha": coding_run.alpha,
            "promotion_status": coding_run.promotion_status,
            "method": coding_run.reliability_method,
        },
        "primary": {
            "fleiss_kappa": fleiss_kappa(primary_rows),
            "krippendorff_alpha": krippendorff_alpha(primary_rows),
            "distinct_codes": len({v for r in primary_rows for v in r}),
        },
        "exact_label_sets": {
            "fleiss_kappa": fleiss_kappa(exact_rows),
            "krippendorff_alpha": krippendorff_alpha(exact_rows),
            "distinct_codes": len({v for r in exact_rows for v in r}),
        },
        "accuracy_vs_planted_theme": accuracy if with_codebook else "n/a (open coding)",
        "_rows": {u: primary.get(u, {}) for u in unit_ids},
        "_coders": coders,
        "_unit_ids": unit_ids,
    }


def attribute(arm_a: dict, arm_b: dict, paired: dict) -> dict:
    """DEC-3's rules, in order; more than one cause may hold."""
    causes = {}
    for arm in (arm_a, arm_b):
        k_primary = arm["primary"]["fleiss_kappa"]
        k_exact = arm["exact_label_sets"]["fleiss_kappa"]
        if k_primary is not None and k_exact is not None:
            causes.setdefault("a_metric_artifact", {})[arm["arm"]] = {
                "kappa_primary": round(k_primary, 4),
                "kappa_exact": round(k_exact, 4),
                "holds": k_primary - k_exact >= 0.20,
            }
    kappa = paired["kappa"]
    causes["b_codebook"] = {
        "kappa_difference": kappa["difference"],
        "p_holm": kappa["p_holm"],
        "holds": kappa["difference"] >= 0.20 and kappa["p_holm"] < 0.05,
    }
    accuracies = [v["accuracy"] or 0.0 for v in arm_b["accuracy_vs_planted_theme"].values()]
    low = [a for a in accuracies if a < 0.60]
    high = [a for a in accuracies if a >= 0.70]
    causes["c_prompt_or_model"] = {
        "accuracies": accuracies,
        "holds": bool(low) and len(low) + len(high) == len(accuracies) and bool(high),
    }
    k_b = arm_b["primary"]["fleiss_kappa"]
    causes["d_genuine_ambiguity"] = {
        "holds": bool(accuracies) and min(accuracies) >= 0.70 and (k_b or 0) < 0.40,
    }
    return causes


async def run(qrels_path: str, per_theme: int) -> dict:
    qrels = json.load(open(qrels_path, encoding="utf-8"))
    units = select_units(qrels, per_theme)
    arm_a = await _run_arm("A", units, with_codebook=False)
    arm_b = await _run_arm("B", units, with_codebook=True)
    # Units pair by position: both arms hold the same quotes in the same order.
    coders_a, coders_b = arm_a.pop("_coders"), arm_b.pop("_coders")
    ids_a, ids_b = arm_a.pop("_unit_ids"), arm_b.pop("_unit_ids")
    rows_a, rows_b = arm_a.pop("_rows"), arm_b.pop("_rows")
    pairs = [
        (
            [rows_a[ua][c] for c in coders_a],
            [rows_b[ub][c] for c in coders_b],
        )
        for ua, ub in zip(ids_a, ids_b, strict=True)
        if all(c in rows_a[ua] for c in coders_a) and all(c in rows_b[ub] for c in coders_b)
    ]
    a_rows = [p[0] for p in pairs]
    b_rows = [p[1] for p in pairs]
    paired = {
        "pairs": len(pairs),
        "kappa": paired_bootstrap(a_rows, b_rows, fleiss_kappa),
        "alpha": paired_bootstrap(a_rows, b_rows, krippendorff_alpha),
        "unit_agreement_mean": {
            "A": round(sum(map(unit_agreement, a_rows)) / len(a_rows), 4) if a_rows else None,
            "B": round(sum(map(unit_agreement, b_rows)) / len(b_rows), 4) if b_rows else None,
        },
    }
    from app.evals.stats import holm_adjust

    adjusted = holm_adjust({"kappa": paired["kappa"]["p"], "alpha": paired["alpha"]["p"]})
    paired["kappa"]["p_holm"] = round(adjusted["kappa"], 4)
    paired["alpha"]["p_holm"] = round(adjusted["alpha"], 4)
    return {
        "measure": "C2/C3 coding agreement with and without a codebook (DEC-3)",
        "units": len(units),
        "per_theme": per_theme,
        "seed": SEED,
        "arms": [arm_a, arm_b],
        "paired_b_minus_a": paired,
        "dec3": attribute(arm_a, arm_b, paired),
        "c3_gate_kappa_arm_b": arm_b["gate"]["kappa"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--qrels", required=True)
    parser.add_argument("--per-theme", type=int, default=5)
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    import app.core.agentic  # noqa: F401  (import-order guard)
    from app.models.database import register_models

    register_models()
    report = asyncio.run(run(args.qrels, args.per_theme))
    text = json.dumps(report, indent=2, default=str)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
