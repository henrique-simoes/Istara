"""Contract tests for the crash-safe budget ledger (B0 scheduling). Pure tier-T0."""

from __future__ import annotations

import json
import multiprocessing
from pathlib import Path

import pytest

from tests.pi_benchmark.budget_ledger import (
    BudgetExceeded,
    BudgetLedger,
    LedgerClosed,
)

pytestmark = pytest.mark.benchmark


def _row_types(path: Path) -> list[str]:
    return [json.loads(line)["type"] for line in path.read_text().splitlines()]


def _hammer_reserve(path_str: str, cap: float, prefix: str, attempts: int, cost: float) -> None:
    """Multiprocessing worker: hammer reserve until the cap refuses further bookings."""
    ledger = BudgetLedger(path_str, cap_usd=cap)
    for index in range(attempts):
        try:
            ledger.reserve(f"{prefix}-{index}", cost, kind="wave")
        except BudgetExceeded:
            return


def test_reserve_commit_release_arithmetic(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)
    ledger.reserve("a", 0.30, kind="judge")
    assert ledger.spent_usd() == pytest.approx(0.30)
    assert ledger.outstanding() == {"a": 0.30}

    ledger.commit("a", 0.12, usage={"input_tokens": 100, "output_tokens": 50})
    assert ledger.spent_usd() == pytest.approx(0.12)
    assert ledger.outstanding() == {}

    ledger.reserve("b", 0.20, kind="judge")
    ledger.release("b", reason="missing_api_key")
    assert ledger.spent_usd() == pytest.approx(0.12)
    assert ledger.outstanding() == {}
    assert _row_types(ledger.path) == ["reserve", "commit", "reserve", "release"]


def test_budget_exhaustion_appends_nothing(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    ledger.reserve("big", 0.60, kind="judge")
    rows_before = path.read_text()
    with pytest.raises(BudgetExceeded):
        ledger.reserve("over", 0.41, kind="judge")
    # The refused reservation appended nothing; a booking that still fits succeeds.
    assert path.read_text() == rows_before
    ledger.reserve("fits", 0.40, kind="judge")
    with pytest.raises(BudgetExceeded):
        ledger.reserve("epsilon-over", 1e-6, kind="judge")


def test_crash_resume_reconstructs_from_file(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    ledger.reserve("in-flight", 0.55, kind="judge")
    del ledger  # simulate a crashed wave process: no cleanup, object dropped

    reopened = BudgetLedger(path, cap_usd=1.00)
    assert reopened.outstanding() == {"in-flight": 0.55}
    assert reopened.spent_usd() == pytest.approx(0.55)
    # The reopened ledger keeps enforcing the cap from the durable record.
    with pytest.raises(BudgetExceeded):
        reopened.reserve("too-much", 0.46, kind="judge")


def test_unknown_usage_reservation_blocks_near_cap_fail_closed(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)
    # A dispatched call whose usage is unknown keeps its worst case booked: the
    # reservation is neither committed nor released (fail closed).
    ledger.reserve("unknown-usage", 0.70, kind="judge")
    with pytest.raises(BudgetExceeded):
        ledger.reserve("next", 0.31, kind="judge")
    # ...but bookings that still fit under the worst case proceed.
    ledger.reserve("ok", 0.30, kind="judge")
    assert ledger.spent_usd() == pytest.approx(1.00)


def test_concurrent_processes_never_exceed_cap(tmp_path):
    path = tmp_path / "ledger.jsonl"
    cap, cost, attempts = 0.10, 0.01, 50
    context = multiprocessing.get_context("fork")
    processes = [
        context.Process(
            target=_hammer_reserve,
            args=(str(path), cap, f"p{worker}", attempts, cost),
        )
        for worker in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=60)
        assert process.exitcode == 0

    ledger = BudgetLedger(path, cap_usd=cap)
    # Total booked spend (committed + outstanding) never crossed the cap...
    assert ledger.spent_usd() <= cap + 1e-9
    assert ledger.spent_usd() == pytest.approx(cap)  # ...and the cap was fully used.
    # ...and concurrent appends never corrupted the JSONL: every line parses.
    lines = path.read_text().splitlines()
    assert len(lines) == 10
    for line in lines:
        assert json.loads(line)["type"] == "reserve"


def test_close_idempotent_and_seals_the_ledger(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    ledger.reserve("a", 0.25, kind="judge")
    ledger.commit("a", 0.10, usage={"input_tokens": 10, "output_tokens": 5})
    ledger.reserve("b", 0.05, kind="judge")

    first = ledger.close()
    assert first == {
        "cap_usd": 1.00,
        "spent_usd": pytest.approx(0.15),
        "committed_usd": pytest.approx(0.10),
        "reserved_outstanding_usd": pytest.approx(0.05),
        "row_count": 4,  # reserve + commit + reserve + close
        "closed": True,
    }
    second = ledger.close()
    assert second == first
    assert _row_types(path) == ["reserve", "commit", "reserve", "close"]  # no dup close

    assert ledger.closed is True
    with pytest.raises(LedgerClosed):
        ledger.reserve("late", 0.01, kind="judge")
    with pytest.raises(LedgerClosed):
        ledger.commit("b", 0.01, usage={})
    with pytest.raises(LedgerClosed):
        ledger.release("b", reason="too_late")
    # A reopened handle sees the sealed state purely from the file.
    assert BudgetLedger(path).closed is True


def test_secret_meta_refused_and_appends_nothing(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    with pytest.raises(ValueError, match="secret"):
        ledger.reserve("a", 0.10, kind="judge", meta={"api_key": "sk-nope"})
    with pytest.raises(ValueError, match="secret"):
        ledger.commit("a", 0.01, usage={}, meta={"access_token": "nope"})
    assert not path.exists()  # nothing was ever appended


@pytest.mark.parametrize("amount", [-0.01, float("nan"), float("inf"), float("-inf")])
def test_non_finite_or_negative_amounts_are_rejected_without_rows(tmp_path, amount):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    with pytest.raises(ValueError):
        ledger.reserve("bad", amount, kind="benchmark")
    assert not path.exists()


def test_call_lifecycle_is_idempotency_safe_and_bounded(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    ledger.reserve("call", 0.40, kind="benchmark")

    with pytest.raises(ValueError, match="already has a reservation"):
        ledger.reserve("call", 0.40, kind="benchmark")
    with pytest.raises(ValueError, match="exceeds its reservation"):
        ledger.commit("call", 0.41, usage={})
    assert _row_types(path) == ["reserve"]

    ledger.commit("call", 0.20, usage={})
    with pytest.raises(ValueError, match="no outstanding reservation"):
        ledger.commit("call", 0.20, usage={})
    with pytest.raises(ValueError, match="no outstanding reservation"):
        ledger.release("call", reason="duplicate")
    assert ledger.spent_usd() == pytest.approx(0.20)


def test_orphan_transitions_are_rejected_without_rows(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ledger = BudgetLedger(path, cap_usd=1.00)
    with pytest.raises(ValueError, match="no outstanding reservation"):
        ledger.commit("ghost", 0.01, usage={})
    with pytest.raises(ValueError, match="no outstanding reservation"):
        ledger.release("ghost", reason="missing")
    assert not path.exists()
