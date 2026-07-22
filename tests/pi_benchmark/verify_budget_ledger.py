"""B0-gate budget-ledger verifier for the live benchmark waves.

Replays the shared crash-safe ledger and proves, from the durable rows alone:

- every row is a known type with the fields that type requires;
- every commit/release references a prior reservation (no orphan spend);
- committed + still-outstanding reservations never exceed the cap (fail closed);
- optionally seals the ledger (``--close``) so no later wave can mutate it.

Exit codes: 0 = ledger consistent and within cap; 1 = violation; 2 = usage error.

Import-safe at T0: touches no backend, DB, network, keychain, or model.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow both invocation styles (`python -m tests.pi_benchmark.verify_budget_ledger`
# and the plan's §5 `python tests/pi_benchmark/verify_budget_ledger.py`).
if __package__ in (None, ""):  # pragma: no cover - only hit in script mode
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tests.pi_benchmark.budget_ledger import BudgetLedger

_EPSILON_USD = 1e-9


def verify_ledger(path: Path, *, cap_usd: float, close: bool = False) -> list[str]:
    """Replay ``path`` and return a list of violations (empty = consistent)."""
    violations: list[str] = []
    ledger = BudgetLedger(path, cap_usd=cap_usd)
    if close:
        ledger.close()
    rows = ledger._read_rows()
    reserved: set[str] = set()
    settled: set[str] = set()
    for index, row in enumerate(rows, start=1):
        row_type = row.get("type")
        if row_type == "reserve":
            if not row.get("call_id") or "max_cost_usd" not in row:
                violations.append(f"row {index}: reserve missing call_id/max_cost_usd")
                continue
            reserved.add(row["call_id"])
        elif row_type in ("commit", "release"):
            call_id = row.get("call_id")
            if call_id not in reserved:
                violations.append(f"row {index}: {row_type} for unreserved call_id {call_id!r}")
            elif call_id in settled:
                violations.append(f"row {index}: {row_type} for already-settled call_id {call_id!r}")
            settled.add(call_id)
            if row_type == "commit" and "actual_cost_usd" not in row:
                violations.append(f"row {index}: commit missing actual_cost_usd")
        elif row_type == "close":
            pass
        else:
            violations.append(f"row {index}: unknown row type {row_type!r}")
    spent = ledger.spent_usd()
    if spent > cap_usd + _EPSILON_USD:
        violations.append(f"spent ${spent:.6f} exceeds cap ${cap_usd:.2f}")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="verify-budget-ledger",
        description="Replay the shared benchmark budget ledger and prove it is within cap.",
    )
    parser.add_argument("--ledger", default=None, help="path to the budget ledger file")
    parser.add_argument("--runs", default=None,
                        help="run directory containing budget-ledger.json (alternative to --ledger)")
    parser.add_argument("--cap-usd", type=float, default=1.00)
    parser.add_argument("--provider", default="deepseek",
                        help="expected provider identity (reported; enforced by the manifest/runner)")
    parser.add_argument("--close", action="store_true",
                        help="seal the ledger before verifying (idempotent)")
    ns = parser.parse_args(argv)

    if ns.provider != "deepseek":
        print(f"[violation] provider {ns.provider!r} is not the approved 'deepseek'", file=sys.stderr)
        return 1
    if ns.ledger:
        ledger_path = Path(ns.ledger)
    elif ns.runs:
        ledger_path = Path(ns.runs) / "budget-ledger.json"
    else:
        parser.error("one of --ledger or --runs is required")
    if not ledger_path.is_file():
        print(f"[violation] ledger {ledger_path} does not exist", file=sys.stderr)
        return 1

    violations = verify_ledger(ledger_path, cap_usd=ns.cap_usd, close=ns.close)
    ledger = BudgetLedger(ledger_path, cap_usd=ns.cap_usd)
    tally = ledger.close() if ns.close else {
        "spent_usd": ledger.spent_usd(),
        "closed": ledger.closed,
        "row_count": len(ledger._read_rows()),
    }
    if violations:
        for violation in violations:
            print(f"[violation] {violation}", file=sys.stderr)
        return 1
    print(
        f"[ok] ledger {ledger_path}: spent=${tally['spent_usd']:.6f} "
        f"<= cap=${ns.cap_usd:.2f}, rows={tally['row_count']}, "
        f"closed={tally['closed']}, provider={ns.provider}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
