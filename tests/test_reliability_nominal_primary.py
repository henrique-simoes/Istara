"""C1/D-8: nominal reliability follows the protocol's primary code, not exact free-text label sets.

The protocol asks each coder for one `primary_code` "when a nominal reliability matrix is
required", but the gate compared each coder's exact set of labels: three coders who all chose
"Pricing concern" as their primary code scored as disagreeing when one wrote it "pricing_concern"
or added a secondary code.
"""

from __future__ import annotations

from app.core.research_validity import evaluate_reliability_gate

UNITS = [f"u{i}" for i in range(6)]
THEMES = ["Pricing concern", "Invoice chasing", "Bank export mismatch"]


def _apps(label_for):
    apps = []
    for coder in ("c1", "c2", "c3"):
        for index, unit in enumerate(UNITS):
            primary, codes = label_for(coder, index)
            apps.append(
                {
                    "coder_id": coder,
                    "model_name": f"model-{coder}",
                    "evidence_unit_id": unit,
                    "primary_code": primary,
                    "codes": codes,
                }
            )
    return apps


def test_same_primary_code_in_different_spellings_and_extra_codes_is_agreement():
    def label(coder, index):
        theme = THEMES[index % 3]
        if coder == "c1":
            return theme, [theme]
        if coder == "c2":
            return theme.lower().replace(" ", "_"), [theme.lower().replace(" ", "_"), "tone:frustrated"]
        return f"  {theme.upper()} ", [theme.upper(), "secondary"]

    gate = evaluate_reliability_gate(_apps(label), threshold=0.6, minimum_distinct_models=3)
    assert gate["kappa"] == 1.0
    assert gate["promotion_status"] == "accepted"


def test_different_primary_codes_are_disagreement():
    def label(coder, index):
        shift = {"c1": 0, "c2": 1, "c3": 2}[coder]
        theme = THEMES[(index + shift) % 3]
        return theme, [theme]

    gate = evaluate_reliability_gate(_apps(label), threshold=0.6, minimum_distinct_models=3)
    assert gate["kappa"] is not None and gate["kappa"] <= 0
    assert gate["promotion_status"] != "accepted"


def test_without_primary_codes_the_code_set_is_still_compared():
    def label(coder, index):
        theme = THEMES[index % 3]
        return "", [theme] if coder != "c3" else [theme, "extra"]

    gate = evaluate_reliability_gate(_apps(label), threshold=0.6, minimum_distinct_models=3)
    assert gate["kappa"] is not None and gate["kappa"] < 1.0
