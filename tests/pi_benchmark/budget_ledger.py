"""Crash-safe cumulative budget ledger for the live benchmark waves (B0 scheduling).

The "B0 offline scheduling + B1..B_N process waves" plan allows exactly one live
provider (DeepSeek ``deepseek-v4-pro``) under a hard cumulative budget cap of $1.00.
This module is the enforcement point: an append-only JSONL ledger whose file is the
single durable source of truth, safe to share across concurrent wave processes and
safe to resume after a crash.

Discipline (fail closed, matching the plan's budget-cap principle):

- ``reserve`` books a worst-case cost *before* dispatch and refuses (BudgetExceeded)
  when the booking would cross the cap, appending nothing.
- ``commit`` replaces a reservation with the provider-reported actual cost.
- ``release`` cancels a reservation and is ONLY for calls that failed before dispatch
  (no provider usage could exist). A dispatched call with unknown usage must NOT be
  released — its reservation stays booked as worst-case spend.
- ``close`` seals the ledger; every later mutation raises LedgerClosed.

Every read-modify-append runs under an exclusive ``fcntl.flock`` on a sidecar lock
file (``<path>.lock``) so concurrent wave processes cannot double-spend, and every
append is a single ``\\n``-terminated write + ``flush`` + ``os.fsync``.

Import-safe at T0: importing this module touches no backend, DB, network, keychain,
or model (``fcntl`` is imported lazily inside the lock context).
"""

from __future__ import annotations

import contextlib
import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

# Meta keys matching any of these markers (case-insensitive substring) are refused:
# ledger rows must never persist API keys or other secrets.
_SECRET_MARKERS = ("api_key", "apikey", "token", "secret", "password")


class BudgetExceeded(RuntimeError):
    """Raised when a reservation would push booked spend past the cap."""


class LedgerClosed(RuntimeError):
    """Raised when mutating a ledger that already has a close row."""


class LedgerStateError(ValueError):
    """Raised when a call attempts an invalid reservation lifecycle transition."""


@dataclass(frozen=True)
class Pricing:
    """USD per one million tokens, per usage class."""

    input_per_million: float
    output_per_million: float
    cache_read_per_million: float
    cache_write_per_million: float


DEEPSEEK_PRICING = Pricing(0.55, 2.19, 0.14, 0.55)  # USD per 1M tokens


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check_meta(meta: dict | None) -> None:
    """Refuse to persist meta carrying anything that looks like a secret."""
    if not meta:
        return
    for key in meta:
        lowered = str(key).lower()
        if any(marker in lowered for marker in _SECRET_MARKERS):
            raise ValueError(
                f"meta key {key!r} looks like a secret; ledger rows never persist secrets"
            )


@contextlib.contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Hold an exclusive advisory lock on the sidecar ``<path>.lock`` file.

    ``fcntl`` is imported lazily so importing this module stays POSIX-portable-safe
    and side-effect free; the lock itself is what serializes concurrent wave
    processes around each read-modify-append.
    """
    import fcntl

    lock_path = path.with_name(path.name + ".lock")
    with open(lock_path, "a") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class BudgetLedger:
    """Append-only JSONL budget ledger with a hard cumulative cap.

    All state is reconstructed by replaying the file on every call, so re-opening an
    existing ledger after a crash (or from another wave process) resumes exactly
    where the durable record left off — there is no in-memory-only state to lose.
    """

    def __init__(self, path: Path | str, cap_usd: float = 1.00) -> None:
        self._path = Path(path)
        self._cap_usd = float(cap_usd)
        if not math.isfinite(self._cap_usd) or self._cap_usd < 0:
            raise ValueError("cap_usd must be a finite, non-negative number")

    @property
    def path(self) -> Path:
        return self._path

    @property
    def cap_usd(self) -> float:
        return self._cap_usd

    # -- durable replay -----------------------------------------------------

    def _read_rows(self) -> list[dict[str, Any]]:
        """Replay the ledger file, tolerating only a torn final line.

        Each append is one ``\\n``-terminated write + fsync, so the only corruption a
        crash can leave is a partial tail without its newline; that tail is dropped.
        Corruption anywhere else is a hard failure — the ledger is the money record
        and must never be silently misread.
        """
        if not self._path.exists():
            return []
        raw = self._path.read_bytes().decode("utf-8")
        if raw and not raw.endswith("\n"):
            raw = raw[: raw.rfind("\n") + 1] if "\n" in raw else ""
        return [json.loads(line) for line in raw.splitlines() if line.strip()]

    @staticmethod
    def _tally(rows: list[dict[str, Any]]) -> dict[str, Any]:
        committed_usd = 0.0
        committed_ids: set[str] = set()
        released_ids: set[str] = set()
        reservations: dict[str, float] = {}
        closed = False
        for row in rows:
            row_type = row.get("type")
            if row_type == "reserve":
                reservations[row["call_id"]] = float(row["max_cost_usd"])
            elif row_type == "commit":
                committed_usd += float(row["actual_cost_usd"])
                committed_ids.add(row["call_id"])
            elif row_type == "release":
                released_ids.add(row["call_id"])
            elif row_type == "close":
                closed = True
        outstanding = {
            call_id: amount
            for call_id, amount in reservations.items()
            if call_id not in committed_ids and call_id not in released_ids
        }
        return {
            "committed_usd": committed_usd,
            "reserved_ids": set(reservations),
            "committed_ids": committed_ids,
            "released_ids": released_ids,
            "outstanding": outstanding,
            "closed": closed,
        }

    @staticmethod
    def _amount(value: float, *, field: str) -> float:
        """Normalize and validate a monetary amount before it reaches JSONL."""
        if isinstance(value, bool):
            raise ValueError(f"{field} must be a finite, non-negative number")
        try:
            amount = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be a finite, non-negative number") from exc
        if not math.isfinite(amount) or amount < 0:
            raise ValueError(f"{field} must be a finite, non-negative number")
        return amount

    def _append_row(self, row: dict[str, Any]) -> None:
        line = json.dumps(row, sort_keys=True) + "\n"
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    # -- queries --------------------------------------------------------------

    def spent_usd(self) -> float:
        """Committed spend plus still-outstanding reservations (worst case)."""
        tally = self._tally(self._read_rows())
        return tally["committed_usd"] + sum(tally["outstanding"].values())

    def outstanding(self) -> dict[str, float]:
        """call_id -> reserved USD still counting against the cap."""
        return self._tally(self._read_rows())["outstanding"]

    @property
    def closed(self) -> bool:
        return self._tally(self._read_rows())["closed"]

    # -- mutations (each serialized under the flock) ---------------------------

    def reserve(
        self,
        call_id: str,
        max_cost_usd: float,
        *,
        kind: str,
        meta: dict | None = None,
    ) -> None:
        """Book ``max_cost_usd`` against the cap for ``call_id`` (pre-dispatch).

        Raises BudgetExceeded (appending nothing) when the booking would cross the
        cap, and LedgerClosed once the ledger is closed.
        """
        if not isinstance(call_id, str) or not call_id:
            raise ValueError("call_id must be a non-empty string")
        max_cost_usd = self._amount(max_cost_usd, field="max_cost_usd")
        _check_meta(meta)
        with _locked(self._path):
            rows = self._read_rows()
            tally = self._tally(rows)
            if tally["closed"]:
                raise LedgerClosed(
                    f"ledger {self._path} is closed; no new reservations"
                )
            if call_id in tally["reserved_ids"]:
                raise LedgerStateError(f"call_id {call_id!r} already has a reservation")
            booked = tally["committed_usd"] + sum(tally["outstanding"].values())
            if booked + max_cost_usd > self._cap_usd:
                raise BudgetExceeded(
                    f"reserve {call_id!r} for {max_cost_usd:.6f} USD would cross the "
                    f"{self._cap_usd:.2f} USD cap (booked so far: {booked:.6f})"
                )
            row: dict[str, Any] = {
                "type": "reserve",
                "call_id": call_id,
                "ts": _utc_now_iso(),
                "kind": kind,
                "max_cost_usd": max_cost_usd,
            }
            if meta is not None:
                row["meta"] = meta
            self._append_row(row)

    def commit(
        self,
        call_id: str,
        actual_cost_usd: float,
        *,
        usage: dict,
        meta: dict | None = None,
    ) -> None:
        """Replace the ``call_id`` reservation with provider-reported actual cost."""
        if not isinstance(call_id, str) or not call_id:
            raise ValueError("call_id must be a non-empty string")
        actual_cost_usd = self._amount(actual_cost_usd, field="actual_cost_usd")
        if not isinstance(usage, dict):
            raise ValueError("usage must be a dict")
        _check_meta(meta)
        with _locked(self._path):
            tally = self._tally(self._read_rows())
            if tally["closed"]:
                raise LedgerClosed(f"ledger {self._path} is closed; refusing commit")
            reservation = tally["outstanding"].get(call_id)
            if reservation is None:
                raise LedgerStateError(
                    f"call_id {call_id!r} has no outstanding reservation to commit"
                )
            if actual_cost_usd > reservation:
                raise LedgerStateError(
                    f"commit {call_id!r} for {actual_cost_usd:.6f} USD exceeds its "
                    f"reservation of {reservation:.6f} USD"
                )
            row: dict[str, Any] = {
                "type": "commit",
                "call_id": call_id,
                "ts": _utc_now_iso(),
                "actual_cost_usd": actual_cost_usd,
                "usage": usage,
            }
            if meta is not None:
                row["meta"] = meta
            self._append_row(row)

    def release(self, call_id: str, *, reason: str) -> None:
        """Cancel the ``call_id`` reservation.

        ONLY for calls that failed before dispatch, where no provider usage could
        exist. A dispatched call with unknown usage must NOT be released — its
        reservation stays booked as worst-case spend (fail closed).
        """
        if not isinstance(call_id, str) or not call_id:
            raise ValueError("call_id must be a non-empty string")
        with _locked(self._path):
            tally = self._tally(self._read_rows())
            if tally["closed"]:
                raise LedgerClosed(f"ledger {self._path} is closed; refusing release")
            if call_id not in tally["outstanding"]:
                raise LedgerStateError(
                    f"call_id {call_id!r} has no outstanding reservation to release"
                )
            self._append_row(
                {
                    "type": "release",
                    "call_id": call_id,
                    "ts": _utc_now_iso(),
                    "reason": reason,
                }
            )

    def close(self) -> dict:
        """Seal the ledger and return the final tally. Idempotent.

        The second and later calls return the same tally without appending a
        duplicate close row.
        """
        with _locked(self._path):
            rows = self._read_rows()
            tally = self._tally(rows)
            if not tally["closed"]:
                self._append_row({"type": "close", "ts": _utc_now_iso()})
                rows = self._read_rows()
        committed = tally["committed_usd"]
        outstanding_sum = sum(tally["outstanding"].values())
        return {
            "cap_usd": self._cap_usd,
            "spent_usd": committed + outstanding_sum,
            "committed_usd": committed,
            "reserved_outstanding_usd": outstanding_sum,
            "row_count": len(rows),
            "closed": True,
        }
