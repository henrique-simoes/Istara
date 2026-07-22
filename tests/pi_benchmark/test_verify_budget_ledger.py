"""Contract tests for the B0-gate budget-ledger verifier. Pure tier-T0."""

from __future__ import annotations

import pytest

from tests.pi_benchmark import verify_budget_ledger
from tests.pi_benchmark.budget_ledger import BudgetLedger

pytestmark = pytest.mark.benchmark


def _ledger(path, rows=()):
    ledger = BudgetLedger(path, cap_usd=1.00)
    for call_id, reserved, actual in rows:
        ledger.reserve(call_id, reserved, kind="benchmark")
        if actual is not None:
            ledger.commit(call_id, actual, usage={"input_tokens": 1, "output_tokens": 1})
    return ledger


def test_consistent_ledger_within_cap_passes(tmp_path, capsys):
    path = tmp_path / "ledger.json"
    _ledger(path, [("a", 0.10, 0.05), ("b", 0.20, None)])  # b still reserved
    assert verify_budget_ledger.main(["--ledger", str(path)]) == 0
    out = capsys.readouterr().out
    assert "[ok]" in out and "spent=$0.2500000"[:12] in out


def test_over_cap_spend_is_a_violation(tmp_path, capsys):
    path = tmp_path / "ledger.json"
    ledger = BudgetLedger(path, cap_usd=0.10)
    ledger.reserve("a", 0.09, kind="benchmark")
    ledger.commit("a", 0.09, usage={"input_tokens": 1, "output_tokens": 1})
    # Verify against a SMALLER cap than the ledger was run under.
    assert verify_budget_ledger.main(["--ledger", str(path), "--cap-usd", "0.05"]) == 1
    assert "exceeds cap" in capsys.readouterr().err


def test_orphan_commit_is_a_violation(tmp_path):
    path = tmp_path / "ledger.json"
    path.write_text(
        '{"type": "commit", "call_id": "ghost", "ts": "t", "actual_cost_usd": 0.01, "usage": {}}\n',
        encoding="utf-8",
    )
    assert verify_budget_ledger.main(["--ledger", str(path)]) == 1


def test_unknown_row_type_is_a_violation(tmp_path):
    path = tmp_path / "ledger.json"
    path.write_text('{"type": "embezzle", "ts": "t"}\n', encoding="utf-8")
    assert verify_budget_ledger.main(["--ledger", str(path)]) == 1


def test_missing_ledger_file_is_a_violation(tmp_path):
    assert verify_budget_ledger.main(["--ledger", str(tmp_path / "nope.json")]) == 1


def test_runs_dir_form_resolves_the_default_ledger_name(tmp_path):
    _ledger(tmp_path / "budget-ledger.json", [("a", 0.01, 0.01)])
    assert verify_budget_ledger.main(["--runs", str(tmp_path)]) == 0


def test_close_seals_the_ledger(tmp_path, capsys):
    path = tmp_path / "ledger.json"
    _ledger(path, [("a", 0.01, 0.01)])
    assert verify_budget_ledger.main(["--ledger", str(path), "--close"]) == 0
    assert "closed=True" in capsys.readouterr().out
    assert BudgetLedger(path).closed is True
    with pytest.raises(Exception):
        BudgetLedger(path).reserve("b", 0.01, kind="benchmark")


def test_non_deepseek_provider_is_rejected(tmp_path):
    path = tmp_path / "ledger.json"
    _ledger(path)
    assert verify_budget_ledger.main(["--ledger", str(path), "--provider", "claude"]) == 1


def test_no_ledger_argument_is_a_usage_error():
    with pytest.raises(SystemExit) as excinfo:
        verify_budget_ledger.main([])
    assert excinfo.value.code == 2
