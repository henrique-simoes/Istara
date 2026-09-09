from scripts.verify_build_stream_status import verify


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
