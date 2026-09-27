"""Inter-coder agreement statistics: Cohen's kappa and Krippendorff's alpha (multi-label).

Pure functions with no model or storage dependency. They lived in the intercoder skill; the
research-validity core imports them, and a core module importing a skill made every import of the
skill's dependencies (windows, runtime seams) a cycle back into core (CF gate, 2026-09-27). The
skill re-exports them for existing callers.
"""

from __future__ import annotations


def cohen_kappa(coder_a: list[list[str]], coder_b: list[list[str]], all_codes: list[str]) -> dict:
    """Calculate Cohen's Kappa from two sets of multi-label codings.

    For multi-label coding (each item can have multiple codes), we calculate
    Kappa per code using binary agreement (code present/absent for each item).

    Args:
        coder_a: List of code lists, one per item. e.g. [["nav", "ux"], ["perf"]]
        coder_b: Same structure from second coder.
        all_codes: Complete list of unique codes across both coders.

    Returns:
        Dict with overall kappa, per-code kappa, interpretation, etc.
    """
    n_items = len(coder_a)
    if n_items == 0 or not all_codes:
        return {
            "kappa": 0.0,
            "interpretation": "poor",
            "observed_agreement": 0.0,
            "expected_agreement": 0.0,
            "n_items_coded": 0,
            "n_codes_used": 0,
            "per_code_kappa": [],
            "low_agreement_codes": [],
        }

    per_code_results = []
    total_agree = 0
    total_items_checked = 0

    for code in all_codes:
        # Binary vectors: 1 if code present, 0 if not
        a_binary = [1 if code in items else 0 for items in coder_a]
        b_binary = [1 if code in items else 0 for items in coder_b]

        # Confusion matrix for this code
        # tp = both say yes, tn = both say no, fp = A no B yes, fn = A yes B no
        tp = sum(1 for a, b in zip(a_binary, b_binary) if a == 1 and b == 1)
        tn = sum(1 for a, b in zip(a_binary, b_binary) if a == 0 and b == 0)
        fp = sum(1 for a, b in zip(a_binary, b_binary) if a == 0 and b == 1)
        fn = sum(1 for a, b in zip(a_binary, b_binary) if a == 1 and b == 0)

        po = (tp + tn) / n_items  # observed agreement
        # Expected agreement by chance
        pa = ((tp + fn) / n_items) * ((tp + fp) / n_items)
        pn = ((tn + fp) / n_items) * ((tn + fn) / n_items)
        pe = pa + pn

        if pe == 1.0:
            code_kappa = 1.0 if po == 1.0 else 0.0
        else:
            code_kappa = (po - pe) / (1 - pe)

        per_code_results.append(
            {
                "code": code,
                "agreement_pct": round(po * 100, 1),
                "kappa": round(code_kappa, 3),
                "frequency_a": tp + fn,
                "frequency_b": tp + fp,
            }
        )

        total_agree += po
        total_items_checked += 1

    # Overall kappa = average of per-code kappas (macro average)
    overall_kappa = (
        sum(r["kappa"] for r in per_code_results) / len(per_code_results)
        if per_code_results
        else 0.0
    )
    overall_agreement = total_agree / total_items_checked if total_items_checked > 0 else 0.0

    # Landis & Koch interpretation
    if overall_kappa < 0.0:
        interpretation = "poor"
    elif overall_kappa <= 0.20:
        interpretation = "slight"
    elif overall_kappa <= 0.40:
        interpretation = "fair"
    elif overall_kappa <= 0.60:
        interpretation = "moderate"
    elif overall_kappa <= 0.80:
        interpretation = "substantial"
    else:
        interpretation = "almost_perfect"

    low_agreement = [r for r in per_code_results if r["kappa"] < 0.60]

    return {
        "kappa": round(overall_kappa, 3),
        "interpretation": interpretation,
        "observed_agreement": round(overall_agreement, 3),
        "expected_agreement": 0.0,  # per-code Pe varies; overall is the macro avg
        "n_items_coded": n_items,
        "n_codes_used": len(all_codes),
        "per_code_kappa": per_code_results,
        "low_agreement_codes": [
            {
                "code": r["code"],
                "kappa": r["kappa"],
                "issue": "Low inter-coder agreement",
                "resolution": "Review code definition for ambiguity",
            }
            for r in low_agreement
        ],
    }


def krippendorff_alpha(coders: list[list[list[str]]], all_codes: list[str]) -> dict:
    """Compute Krippendorff's Alpha for N coders on nominal data.

    More robust than Cohen's Kappa:
    - Handles any number of coders (not just 2)
    - Handles missing data properly
    - Based on Krippendorff (2004, 2011) Content Analysis

    For multi-label coding, we use the binary approach: for each code,
    create a binary (present/absent) reliability matrix, then compute
    alpha per code and average.

    Args:
        coders: List of coders, each containing a list of code lists per item.
                e.g., [coder_a_items, coder_b_items] where each item is a list of codes.
        all_codes: Complete list of unique codes.

    Returns:
        Dict with alpha, per-code alpha, interpretation.
    """
    n_coders = len(coders)
    if n_coders == 0 or not all_codes:
        return {
            "alpha": 0.0,
            "interpretation": "unreliable",
            "n_coders": 0,
            "n_items": 0,
            "n_codes": 0,
            "per_code_alpha": [],
            "unreliable_codes": [],
        }

    # All coders must have the same number of items; use the minimum if they differ
    n_items = min(len(c) for c in coders) if coders else 0
    if n_items == 0:
        return {
            "alpha": 0.0,
            "interpretation": "unreliable",
            "n_coders": n_coders,
            "n_items": 0,
            "n_codes": len(all_codes),
            "per_code_alpha": [],
            "unreliable_codes": [],
        }

    per_code_results = []

    for code in all_codes:
        # Build binary reliability matrix: rows = items, columns = coders
        # Value is 1 if code present, 0 if absent, None if missing
        matrix: list[list[int | None]] = []
        for i in range(n_items):
            row = []
            for c in range(n_coders):
                if i < len(coders[c]) and coders[c][i] is not None:
                    row.append(1 if code in coders[c][i] else 0)
                else:
                    row.append(None)  # missing data
            matrix.append(row)

        # Compute observed disagreement Do
        # For each item, count pairwise disagreements among coders who coded it
        total_do_numerator = 0.0
        total_pairable = 0  # total number of pairable values across all items

        for row in matrix:
            values = [v for v in row if v is not None]
            m_u = len(values)  # number of coders for this item
            if m_u < 2:
                continue  # need at least 2 coders to compare
            total_pairable += m_u
            # Count disagreements in all pairs within this item
            disagreements = 0
            for vi in range(len(values)):
                for vj in range(vi + 1, len(values)):
                    if values[vi] != values[vj]:
                        disagreements += 1
            # Krippendorff (2004): weight by 1/(m_u - 1) for each item
            total_do_numerator += disagreements / (m_u - 1)

        if total_pairable == 0:
            per_code_results.append(
                {
                    "code": code,
                    "alpha": 0.0,
                }
            )
            continue

        do = total_do_numerator / total_pairable  # observed disagreement (normalized)

        # Compute expected disagreement De from marginal frequencies
        # Count total 1s and 0s across all non-missing values
        n_ones = 0
        n_zeros = 0
        for row in matrix:
            for v in row:
                if v is not None:
                    if v == 1:
                        n_ones += 1
                    else:
                        n_zeros += 1
        n_total = n_ones + n_zeros
        if n_total < 2:
            per_code_results.append(
                {
                    "code": code,
                    "alpha": 0.0,
                }
            )
            continue

        # For nominal metric: De = (n_ones * n_zeros) / (n_total * (n_total - 1) / 2)
        # Simplified: De = 2 * (n_ones / n_total) * (n_zeros / n_total) * n_total / (n_total - 1)
        de = (2 * n_ones * n_zeros) / (n_total * (n_total - 1))

        if de == 0.0:
            code_alpha = 1.0  # perfect agreement (all values identical)
        else:
            code_alpha = 1.0 - (do / de)

        per_code_results.append(
            {
                "code": code,
                "alpha": round(code_alpha, 3),
            }
        )

    # Overall alpha = average of per-code alphas (macro average)
    if per_code_results:
        overall_alpha = sum(r["alpha"] for r in per_code_results) / len(per_code_results)
    else:
        overall_alpha = 0.0

    overall_alpha = round(overall_alpha, 3)

    # Krippendorff (2004) interpretation scale
    if overall_alpha >= 0.800:
        interpretation = "reliable"
    elif overall_alpha >= 0.667:
        interpretation = "tentatively_acceptable"
    else:
        interpretation = "unreliable"

    unreliable_codes = [
        {
            "code": r["code"],
            "alpha": r["alpha"],
            "issue": "Below reliability threshold",
            "resolution": "Review code definition and coder training",
        }
        for r in per_code_results
        if r["alpha"] < 0.667
    ]

    return {
        "alpha": overall_alpha,
        "interpretation": interpretation,
        "n_coders": n_coders,
        "n_items": n_items,
        "n_codes": len(all_codes),
        "per_code_alpha": per_code_results,
        "unreliable_codes": unreliable_codes,
    }
