"""C2 harness: agreement statistics match published worked examples; DEC-3 rules as written."""

from __future__ import annotations

from app.evals.coding_agreement_eval import (
    CODEBOOK,
    THEME_CODE,
    attribute,
    fleiss_kappa,
    krippendorff_alpha,
    paired_bootstrap,
    select_units,
)

# Fleiss (1971) worked example as tabulated on Wikipedia: 10 subjects, 14 raters, 5 categories.
FLEISS_TABLE = [
    [0, 0, 0, 0, 14],
    [0, 2, 6, 4, 2],
    [0, 0, 3, 5, 6],
    [0, 3, 9, 2, 0],
    [2, 2, 8, 1, 1],
    [7, 7, 0, 0, 0],
    [3, 2, 6, 3, 0],
    [2, 5, 3, 2, 2],
    [6, 5, 2, 1, 0],
    [0, 2, 2, 3, 7],
]

# Krippendorff (2011), "Computing Krippendorff's Alpha-Reliability", nominal example: alpha 0.743.
KRIPPENDORFF_UNITS = [
    ["1", "1", "1"],
    ["2", "2", "3", "2"],
    ["3", "3", "3", "3"],
    ["3", "3", "3", "3"],
    ["2", "2", "2", "2"],
    ["1", "2", "3", "4"],
    ["4", "4", "4", "4"],
    ["1", "1", "2", "1"],
    ["2", "2", "2", "2"],
    ["5", "5", "5"],
    ["1", "1"],
    ["3"],
]


def test_fleiss_kappa_matches_the_worked_example():
    rows = [
        [str(category) for category, count in enumerate(counts) for _ in range(count)]
        for counts in FLEISS_TABLE
    ]
    assert round(fleiss_kappa(rows), 3) == 0.210


def test_krippendorff_alpha_matches_the_worked_example():
    assert round(krippendorff_alpha(KRIPPENDORFF_UNITS), 3) == 0.743


def test_perfect_and_rotated_agreement():
    perfect = [[c, c, c] for c in "abcabcabc"]
    assert fleiss_kappa(perfect) == 1.0 and krippendorff_alpha(perfect) == 1.0
    rotated = [["a", "b", "c"], ["b", "c", "a"], ["c", "a", "b"]] * 3
    assert fleiss_kappa(rotated) < 0 and krippendorff_alpha(rotated) < 0.1


def test_units_are_fixed_by_the_seed_and_balanced_across_themes():
    qrels = {
        "questions": [
            {"theme": f"T{t}", "targets": [f"quote {t}-{i}" for i in range(8)]}
            for t in range(1, 11)
        ]
    }
    units = select_units(qrels, per_theme=5)
    assert units == select_units(qrels, per_theme=5)
    assert len(units) == 50
    assert all(sum(1 for th, _ in units if th == f"T{t}") == 5 for t in range(1, 11))


def test_codebook_covers_every_theme_with_definitions_and_criteria():
    assert set(THEME_CODE) == {f"T{t}" for t in range(1, 11)}
    assert all(e["definition"] and e["include"] and e["exclude"] for e in CODEBOOK)
    assert len(set(THEME_CODE.values())) == 10


def test_paired_bootstrap_detects_a_real_improvement():
    a = [["x", "y", "z"]] * 20 + [["x", "x", "y"]] * 20
    b = [["x", "x", "x"]] * 30 + [["x", "x", "y"]] * 10
    result = paired_bootstrap(a, b, fleiss_kappa, resamples=500)
    assert result["difference"] > 0 and result["p"] < 0.05


def _arm(label, k_primary, k_exact, accuracy=None):
    return {
        "arm": label,
        "primary": {"fleiss_kappa": k_primary},
        "exact_label_sets": {"fleiss_kappa": k_exact},
        "accuracy_vs_planted_theme": accuracy or {},
    }


def test_dec3_rules_as_pre_registered():
    paired = {"kappa": {"difference": 0.45, "p_holm": 0.001}}
    causes = attribute(
        _arm("A", 0.30, 0.02),
        _arm(
            "B",
            0.75,
            0.70,
            {"m1": {"accuracy": 0.9}, "m2": {"accuracy": 0.8}, "m3": {"accuracy": 0.4}},
        ),
        paired,
    )
    assert causes["a_metric_artifact"]["A"]["holds"] is True
    assert causes["a_metric_artifact"]["B"]["holds"] is False
    assert causes["b_codebook"]["holds"] is True
    assert causes["c_prompt_or_model"]["holds"] is True
    assert causes["d_genuine_ambiguity"]["holds"] is False
