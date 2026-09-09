from pathlib import Path

from scripts.verify_build_stream_status import verify

CONVERGENCE = (
    Path(__file__).resolve().parents[1]
    / "docs/build-stream/2026-09-09-testing-to-main-convergence.md"
)


def lifecycle(status_body: str, rows: str) -> str:
    return f"""<!-- STATUS BLOCK -->
```yaml
{status_body}
```
<!-- /STATUS BLOCK -->
| Phase | Goal | Acceptance | Status |
|---|---|---|---|
{rows}
"""


def test_accepts_consistent_active_phase():
    text = lifecycle(
        'item: x\nphase: "Phase 2 — truth"\nstage: S4-remediate\nnext_action: "Run delta re-review."',
        "| 0 | plan | vote | done |\n| 1 | freeze | sha | done |\n| 2 | truth | check | in-progress |\n| 3 | fix | tests | planned |",
    )
    assert verify(text) == []


def test_rejects_duplicate_key_stale_progression_and_action():
    text = lifecycle(
        'item: x\ncf: one\ncf: two\nphase: "Phase 2 — truth"\nstage: S3-review\nnext_action: "Conductor may dispatch implementation."',
        "| 0 | plan | vote | in-progress |\n| 1 | freeze | sha | planned |\n| 2 | truth | check | planned |",
    )
    errors = verify(text)
    assert "duplicate status keys: cf" in errors
    assert "active Phase 2 must be in-progress in roadmap" in errors
    assert "earlier phases must be done: 0, 1" in errors
    assert "review/remediation status has stale implementation next_action" in errors


def test_rejects_exact_stale_owner_sync_action():
    text = lifecycle(
        'item: x\nphase: "Phase 2 — truth"\nstage: S4-remediate\n'
        'next_action: "Owner approved MECE master plan (slot b); '
        'conductor may dispatch implementation."',
        "| 0 | plan | vote | done |\n| 1 | freeze | sha | done |\n| 2 | truth | check | in-progress |\n| 3 | fix | tests | planned |",
    )
    assert "review/remediation status has stale implementation next_action" in verify(text)


def test_rejects_ambiguous_last_ledger_pointer():
    text = lifecycle(
        'item: x\nphase: "Phase 2 — truth"\nstage: S4-remediate\n'
        'last: { agent: fixer, at: 2026-09-09T18:00:00Z, ledger: L-21 }\n'
        'next_action: "Run delta re-review."',
        "| 0 | plan | vote | done |\n| 1 | freeze | sha | done |\n| 2 | truth | check | in-progress |\n| 3 | fix | tests | planned |",
    ) + "\n### L-21 | 2026-09-09T17:35:38Z | S4-remediate | a | remediator | truth\n" \
        + "### L-21 | 2026-09-09T17:42:00Z | S4-remediate | b | remediator | truth\n"
    errors = verify(text)
    assert any("last.ledger L-21 is ambiguous" in error for error in errors)


def test_checked_in_convergence_lifecycle_passes_status_verifier():
    errors = verify(CONVERGENCE.read_text(encoding="utf-8"))
    assert errors == []


def test_checked_in_convergence_last_ledger_resolves_uniquely():
    import re

    text = CONVERGENCE.read_text(encoding="utf-8")
    ref = re.search(r"ledger:\s*(L-\d+)", text).group(1)
    count = len(re.findall(rf"^###\s+{ref}\b", text, re.M))
    assert count == 1
