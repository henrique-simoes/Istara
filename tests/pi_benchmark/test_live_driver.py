"""Contract tests for the live dispatcher-path driver (Lane B).

All offline: fakes for the ledger, provider, dispatch, and backend validation module —
no backend import, no network, no keychain. Async driver entry points are exercised via
``asyncio.run`` (no pytest-asyncio dependency).
"""

from __future__ import annotations

import asyncio
import json
import types

import pytest

from tests.pi_benchmark import live_driver, schema
from tests.pi_benchmark.live_driver import LiveCapture
from tests.pi_benchmark.runner import RunConfig
from tests.pi_benchmark.scenarios.base import Scenario

pytestmark = pytest.mark.benchmark


# ── fakes ───────────────────────────────────────────────────────────────────


class FakeLedger:
    """In-memory stand-in for Lane A's BudgetLedger (same call surface)."""

    def __init__(
        self,
        *,
        fail_reserve: bool = False,
        reserve_state_error: bool = False,
        commit_over_reservation: bool = False,
    ):
        self._fail_reserve = fail_reserve
        self._reserve_state_error = reserve_state_error
        self._commit_over_reservation = commit_over_reservation
        self.reserved: dict[str, float] = {}
        self.committed: dict[str, tuple] = {}
        self.released: dict[str, str] = {}

    def reserve(self, call_id, max_cost_usd, *, kind, meta=None):
        if self._fail_reserve:
            raise live_driver.BudgetExceeded("cap reached")
        if self._reserve_state_error:
            # Resume after a crash: this unit already has an outstanding reservation, so
            # a fresh reserve is refused. The booking stays (retained worst-case spend).
            self.reserved[call_id] = max_cost_usd
            raise live_driver.LedgerStateError(f"call_id {call_id!r} already has a reservation")
        self.reserved[call_id] = max_cost_usd

    def commit(self, call_id, actual_cost_usd, *, usage, meta=None):
        if self._commit_over_reservation:
            # Actual cost exceeded the worst-case reservation: the real ledger refuses this.
            raise live_driver.LedgerStateError(f"commit {call_id!r} exceeds its reservation")
        self.committed[call_id] = (actual_cost_usd, usage, meta)

    def release(self, call_id, *, reason):
        self.released[call_id] = reason
        self.reserved.pop(call_id, None)

    def spent_usd(self):
        return sum(v[0] for v in self.committed.values())

    def outstanding(self):
        return {k: v for k, v in self.reserved.items() if k not in self.committed}


class FakeProvider:
    """DeepSeek-priced stand-in for Lane A's DeepSeekProvider."""

    model = "deepseek-v4-pro"

    def __init__(self):
        self.calls = []

    def estimate_cost(self, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0):
        return (
            input_tokens * 0.55 + output_tokens * 2.19
            + cache_read_tokens * 0.14 + cache_write_tokens * 0.55
        ) / 1e6

    def endpoint_fingerprint(self):
        return "deepseek:0123456789ab"

    def chat(self, **kwargs):
        self.calls.append(kwargs)
        return "legacy provider response", types.SimpleNamespace(
            input_tokens=11, output_tokens=7, cache_read_tokens=0,
            cache_write_tokens=0, total_tokens=18, estimate=False,
        )


def _unit(**overrides):
    base = dict(
        unit_id="u-1", pack="canonical", scenario_id="s1", seed=0, repeat=1,
        engine="pi", phase="B2", moa_mode=None,
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


def _scenario():
    return Scenario(id="s1", title="Smoke scenario", pack="canonical")


def _config(tmp_path, **overrides):
    base = dict(
        packs=("canonical",), tier="T3", engines=("pi",), seeds=(0,), repeats=1,
        phase="B2", out_dir=tmp_path,
    )
    base.update(overrides)
    return RunConfig(**base)


def _usage(inp=100, out=50, cr=10, cw=5, total=150):
    return {
        "input_tokens": inp, "output_tokens": out, "cache_read_tokens": cr,
        "cache_write_tokens": cw, "total_tokens": total,
    }


def _capture(**overrides):
    base = dict(
        text="hello live world", usage=_usage(), estimate=False,
        endpoint_ids=("pi-deepseek-default",),
        route_evidence=({"endpoint_id": "pi-deepseek-default", "route_kind": "agentic_ensemble"},),
        raw_method=None,
    )
    base.update(overrides)
    return LiveCapture(**base)


def _dispatch_returning(capture, calls=None):
    async def _dispatch(*, unit, tier, prompt, system, moa_n, max_tokens):
        if calls is not None:
            calls.append({
                "unit": unit, "tier": tier, "prompt": prompt,
                "moa_n": moa_n, "max_tokens": max_tokens,
            })
        return capture
    return _dispatch


def _run(tmp_path, *, unit=None, ledger=None, dispatch, config=None, **kwargs):
    return live_driver.run_live_unit_sync(
        unit=unit or _unit(), scenario=_scenario(), config=config or _config(tmp_path),
        ledger=ledger or FakeLedger(), provider=FakeProvider(),
        records_dir=tmp_path / "records", dispatch=dispatch, **kwargs,
    )


# ── dispatch_unit capture behaviour (injected fakes, no backend import) ─────


def test_dispatch_unit_plain_path_uses_estimator_when_outcome_has_no_usage():
    outcome = types.SimpleNamespace(
        samples=[types.SimpleNamespace(text="x" * 40, usage=None, endpoint_id="ep", status="success")],
        endpoint_ids=["ep"], usage=None,
    )
    seen = {}

    async def ensemble_fn(**kwargs):
        seen.update(kwargs)
        return outcome

    capture = asyncio.run(live_driver.dispatch_unit(
        unit=_unit(), tier="T3", prompt="p" * 20, moa_n=3, max_tokens=37,
        ensemble_fn=ensemble_fn,
    ))
    assert capture.estimate is True
    assert capture.usage["output_tokens"] == 10  # 40 chars / 4
    assert capture.usage["input_tokens"] == 5    # 20 chars / 4
    assert capture.raw_method is None
    # The fake received the pinned DeepSeek params as a plain dict (no backend types).
    assert seen["params"] == {
        "endpoint_id": "pi-deepseek-default", "model": "deepseek-v4-pro", "max_tokens": 37,
    }
    assert seen["engine"] == "pi"
    assert seen["n"] == 1 and seen["distinct"] is False


def test_dispatch_unit_full_ensemble_requests_exactly_moa_n_slots():
    calls = {}

    class FakeAgentic:
        async def ensemble(self, **kwargs):
            calls.update(kwargs)
            return types.SimpleNamespace(
                samples=[
                    types.SimpleNamespace(
                        text=text, usage=None, endpoint_id="pi-deepseek-default", status="success",
                    )
                    for text in ("a", "b", "c")
                ],
                endpoint_ids=["pi-deepseek-default"] * 3,
                usage={}, status="success",
            )

    capture = asyncio.run(live_driver.dispatch_unit(
        unit=_unit(moa_mode="full_ensemble"), tier="T3", prompt="hello",
        moa_n=3, agentic_module=FakeAgentic(),
    ))
    assert calls["n"] == 3 and calls["distinct"] is False
    assert calls["engine"] == "pi"
    assert capture.raw_method == "full_ensemble"
    assert capture.endpoint_ids == ("pi-deepseek-default",) * 3
    assert capture.route_evidence[0]["provider"] == "deepseek"
    assert capture.consensus_confidence in {"high", "medium", "low", "insufficient"}
    assert capture.estimate is True and capture.usage is not None


def test_dispatch_unit_legacy_uses_approved_provider_not_compute_registry():
    provider = FakeProvider()

    class ForbiddenAgentic:
        async def ensemble(self, **kwargs):  # pragma: no cover - must never run
            raise AssertionError("legacy benchmark dispatch must not enter agentic registry path")

    capture = asyncio.run(live_driver.dispatch_unit(
        unit=_unit(engine="legacy"), tier="T3", prompt="hello",
        provider=provider, agentic_module=ForbiddenAgentic(),
    ))

    assert len(provider.calls) == 1
    assert provider.calls[0]["ledger"] is None
    assert provider.calls[0]["call_id"] == "u-1:legacy:1"
    assert capture.text == "legacy provider response"
    assert capture.endpoint_ids == ("pi-deepseek-default",)
    assert capture.route_evidence[0] == {
        "endpoint_id": "pi-deepseek-default",
        "provider": "deepseek",
        "model": "deepseek-v4-pro",
        "engine": "legacy",
        "route_kind": "deepseek_provider",
    }


def test_dispatch_unit_legacy_moa_repeats_approved_provider_route():
    provider = FakeProvider()
    capture = asyncio.run(live_driver.dispatch_unit(
        unit=_unit(engine="legacy", moa_mode="self_moa"), tier="T3", prompt="hello",
        moa_n=3, provider=provider,
    ))

    assert len(provider.calls) == 3
    assert [call["temperature"] for call in provider.calls] == [0.3, 0.7, 1.0]
    assert capture.raw_method == "self_moa"
    assert capture.endpoint_ids == ("pi-deepseek-default",) * 3
    assert all(route["provider"] == "deepseek" for route in capture.route_evidence)


def test_run_live_unit_default_dispatch_forwards_provider_to_legacy(tmp_path):
    provider = FakeProvider()
    record = live_driver.run_live_unit_sync(
        unit=_unit(engine="legacy"), scenario=_scenario(), config=_config(tmp_path),
        ledger=FakeLedger(), provider=provider, records_dir=tmp_path / "records",
    )

    assert record["status"] == "ok"
    assert len(provider.calls) == 1
    assert record["extensions"]["route_evidence"][0]["engine"] == "legacy"
    assert schema.is_valid(record)


def test_dispatch_unit_moa_rejects_an_unapproved_served_route():
    class FakeAgentic:
        async def ensemble(self, **kwargs):
            return types.SimpleNamespace(
                samples=[types.SimpleNamespace(
                    text="local response", usage=None, endpoint_id="pi-local-ollama", status="success",
                )],
                endpoint_ids=["pi-local-ollama"], usage={}, status="success",
            )

    with pytest.raises(live_driver.RouteAdmissionError, match="not approved"):
        asyncio.run(live_driver.dispatch_unit(
            unit=_unit(moa_mode="self_moa"), tier="T3", prompt="hello", moa_n=1,
            agentic_module=FakeAgentic(),
        ))


def test_unapproved_route_is_recorded_without_live_provenance(tmp_path):
    route_error = live_driver.RouteAdmissionError(
        "benchmark route not approved: 'pi-local-ollama'",
        route={
            "endpoint_id": "pi-local-ollama",
            "route_kind": "agentic_ensemble",
            "admission": "rejected",
        },
    )

    async def dispatch(**kwargs):
        raise route_error

    record = _run(tmp_path, dispatch=dispatch)
    assert record["status"] == "not_runnable"
    assert record["provenance"]["model_id"] is None
    assert record["provenance"]["endpoint_fingerprint"] is None
    assert record["extensions"]["detail"] == {"reason": "route_admission_failed"}
    assert record["extensions"]["route_evidence"][0]["admission"] == "rejected"


# ── run_live_unit end-to-end ────────────────────────────────────────────────


def test_ok_record_exact_usage_commit_and_atomic_write(tmp_path):
    ledger = FakeLedger()
    calls = []
    record = _run(tmp_path, ledger=ledger, dispatch=_dispatch_returning(_capture(), calls))

    assert record["status"] == "ok"
    assert schema.is_valid(record)
    usage = record["usage"]
    assert usage["input_tokens"] == 100 and usage["output_tokens"] == 50
    assert usage["cache_tokens"] == 15  # read + write
    assert usage["total_tokens"] == 150
    assert usage["estimate"] is False and usage["estimator"] is None
    expected_cost = round(FakeProvider().estimate_cost(100, 50, 10, 5), 7)
    assert usage["cost_usd"] == pytest.approx(expected_cost)

    # Provenance: DeepSeek model id + redacted fingerprint (never a raw URL).
    assert record["provenance"]["model_id"] == "deepseek-v4-pro"
    fingerprint = record["provenance"]["endpoint_fingerprint"]
    assert fingerprint.startswith("deepseek-route:") and "api.deepseek.com" not in fingerprint
    assert record["extensions"]["route_evidence"][0]["endpoint_id"] == "pi-deepseek-default"

    # Ledger: reserved worst-case, committed actual, nothing outstanding.
    assert "u-1" in ledger.reserved
    prompt = live_driver.default_prompt_builder(_unit(), _scenario())
    reserve_input = max(2 * live_driver._chars4(prompt), live_driver.MIN_RESERVE_INPUT_TOKENS)
    worst_case = FakeProvider().estimate_cost(reserve_input, live_driver.DEFAULT_MAX_TOKENS)
    assert ledger.reserved["u-1"] == pytest.approx(worst_case)
    actual, committed_usage, meta = ledger.committed["u-1"]
    assert actual == pytest.approx(expected_cost)
    assert committed_usage["total_tokens"] == 150
    assert meta == {"estimate": False}
    assert ledger.outstanding() == {}

    # Crash-safe write: final record exists, no tmp left, disk copy validates.
    records_dir = tmp_path / "records"
    on_disk = json.loads((records_dir / "u-1.json").read_text())
    schema.validate_record(on_disk)
    assert list(records_dir.glob("*.tmp")) == []
    assert calls and calls[0]["tier"] == "T3"


def test_run_live_unit_forwards_the_reserved_output_bound(tmp_path):
    calls = []
    record = _run(
        tmp_path, dispatch=_dispatch_returning(_capture(), calls), max_tokens=17,
    )
    assert record["status"] == "ok"
    assert calls[0]["max_tokens"] == 17


def test_estimate_path_names_the_estimator(tmp_path):
    capture = _capture(usage=_usage(25, 10, 0, 0, 35), estimate=True)
    record = _run(tmp_path, dispatch=_dispatch_returning(capture))
    assert record["status"] == "ok"
    assert record["usage"]["estimate"] is True
    assert record["usage"]["estimator"] == "chars4"
    assert schema.is_valid(record)


def test_unknown_usage_after_dispatch_fails_closed_and_retains_reservation(tmp_path):
    ledger = FakeLedger()
    capture = _capture(text="", usage=None, estimate=False, endpoint_ids=(), route_evidence=())
    record = _run(tmp_path, ledger=ledger, dispatch=_dispatch_returning(capture))
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "other"
    assert record["extensions"]["detail"] == "unknown_usage_fail_closed"
    assert ledger.outstanding() == {"u-1": ledger.reserved["u-1"]}  # retained
    assert "u-1" not in ledger.committed and "u-1" not in ledger.released
    assert schema.is_valid(record)


def test_over_reservation_commit_fails_closed_and_retains_reservation(tmp_path):
    # A real call whose actual cost exceeds the worst-case reservation: the ledger refuses
    # the commit. The driver must fail closed — write a terminal record, retain the
    # reservation, and never crash the wave (a crash here would leave no record and wedge
    # the resume on the outstanding reservation).
    ledger = FakeLedger(commit_over_reservation=True)
    record = _run(tmp_path, ledger=ledger, dispatch=_dispatch_returning(_capture()))
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "other"
    assert record["extensions"]["detail"] == "accounting_fail_closed"
    assert ledger.outstanding() == {"u-1": ledger.reserved["u-1"]}  # retained
    assert "u-1" not in ledger.committed and "u-1" not in ledger.released
    assert schema.is_valid(record)
    # A terminal record exists so a resume sees this unit as done (no wedge).
    assert (tmp_path / "records" / "u-1.json").is_file()


def test_resume_with_outstanding_reservation_records_interrupted_and_retains(tmp_path):
    # Simulate resume after a crash that reserved this unit but never wrote its record:
    # re-reserving raises LedgerStateError. The driver must record the interruption and
    # retain the reservation instead of re-raising (which would permanently wedge the wave),
    # and must not re-dispatch.
    ledger = FakeLedger(reserve_state_error=True)

    async def exploding_dispatch(**kwargs):  # pragma: no cover - must never run
        raise AssertionError("interrupted resume must not re-dispatch")

    record = _run(tmp_path, ledger=ledger, dispatch=exploding_dispatch)
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "other"
    assert record["extensions"]["detail"] == "interrupted_unknown_usage"
    assert ledger.outstanding() == {"u-1": ledger.reserved["u-1"]}  # retained
    assert "u-1" not in ledger.committed and "u-1" not in ledger.released
    assert schema.is_valid(record)
    assert (tmp_path / "records" / "u-1.json").is_file()


def test_budget_exceeded_records_the_block_and_never_dispatches(tmp_path):
    ledger = FakeLedger(fail_reserve=True)
    dispatched = []

    async def dispatch(**kwargs):
        dispatched.append(kwargs)
        return _capture()

    record = _run(tmp_path, ledger=ledger, dispatch=dispatch)
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "budget_exceeded"
    assert dispatched == []
    assert schema.is_valid(record)


def test_pre_dispatch_failure_releases_the_reservation(tmp_path):
    ledger = FakeLedger()

    async def dispatch(**kwargs):
        raise live_driver.PreDispatchError("endpoint not admitted")

    record = _run(tmp_path, ledger=ledger, dispatch=dispatch)
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "startup_failure"
    assert "u-1" in ledger.released
    assert ledger.outstanding() == {}


def test_post_dispatch_failure_retains_the_reservation(tmp_path):
    ledger = FakeLedger()

    async def dispatch(**kwargs):
        raise RuntimeError("provider exploded mid-flight")

    record = _run(tmp_path, ledger=ledger, dispatch=dispatch)
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "startup_failure"
    assert ledger.outstanding() == {"u-1": ledger.reserved["u-1"]}  # fail closed
    assert "u-1" not in ledger.released


def test_timeout_maps_to_the_timeout_reason_and_retains(tmp_path):
    ledger = FakeLedger()

    async def dispatch(**kwargs):
        raise TimeoutError("slow provider")

    record = _run(tmp_path, ledger=ledger, dispatch=dispatch)
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "timeout"
    assert ledger.outstanding() != {}


def test_moa_downgrade_is_recorded_not_runnable_with_evidence(tmp_path):
    ledger = FakeLedger()
    capture = _capture(
        endpoint_ids=("ep-a", "ep-b"),
        route_evidence=({"endpoint_id": "ep-a"}, {"endpoint_id": "ep-b"}),
        raw_method="dual_run",
    )
    record = _run(
        tmp_path, unit=_unit(moa_mode="full_ensemble"), ledger=ledger,
        dispatch=_dispatch_returning(capture),
    )
    assert record["status"] == "not_runnable"
    assert record["not_runnable_reason"] == "other"
    evidence = record["extensions"]["moa"]
    assert evidence["downgrade"] == "full_ensemble->dual_run"
    assert evidence["degraded"] is True
    assert evidence["requested_mode"] == "full_ensemble"
    assert evidence["served_mode"] == "dual_run"
    # The spend was real, so the cost is still committed.
    assert "u-1" in ledger.committed
    assert schema.is_valid(record)


def test_moa_clean_self_moa_records_ok_with_evidence(tmp_path):
    capture = _capture(
        endpoint_ids=("pi-deepseek-default",) * 3,
        route_evidence=tuple({"endpoint_id": "pi-deepseek-default"} for _ in range(3)),
        raw_method="self_moa",
    )
    record = _run(
        tmp_path, unit=_unit(moa_mode="self_moa"), dispatch=_dispatch_returning(capture),
    )
    assert record["status"] == "ok"
    evidence = record["extensions"]["moa"]
    assert evidence["reconciliation_status"] == "reconciled"
    assert evidence["distinct_served_routes"] == 1
    assert tuple(evidence["temperatures"]) == (0.3, 0.7, 1.0)
    assert evidence["consensus_score"] is None  # the capture has no consensus object
    assert schema.is_valid(record)


def test_moa_partial_self_moa_fails_closed_even_when_endpoint_list_is_full(tmp_path):
    capture = _capture(
        endpoint_ids=("pi-deepseek-default",) * 3,
        route_evidence=({"endpoint_id": "pi-deepseek-default"},),
        raw_method="self_moa",
        consensus_score=0.9,
        consensus_confidence="high",
    )
    record = _run(
        tmp_path, unit=_unit(moa_mode="self_moa"), dispatch=_dispatch_returning(capture),
    )
    evidence = record["extensions"]["moa"]
    assert record["status"] == "not_runnable"
    assert evidence["response_count"] == 1 and evidence["coder_count"] == 1
    assert evidence["source_unit_ids"] == ("pi-deepseek-default",) * 3
    assert evidence["consensus_score"] == pytest.approx(0.9)
    assert evidence["consensus_confidence"] == "high"
    assert evidence["downgrade"] == "partial_coder"
    assert schema.is_valid(record)


def test_moa_partial_full_ensemble_ignores_failed_selected_routes(tmp_path):
    capture = _capture(
        endpoint_ids=("ep-a", "ep-b", "ep-c"),
        route_evidence=({"endpoint_id": "ep-a"},),
        raw_method="full_ensemble",
        consensus_score=0.9,
        consensus_confidence="high",
    )
    record = _run(
        tmp_path, unit=_unit(moa_mode="full_ensemble"), dispatch=_dispatch_returning(capture),
    )
    evidence = record["extensions"]["moa"]
    assert record["status"] == "not_runnable"
    assert evidence["served_route_ids"] == ("ep-a",)
    assert evidence["distinct_served_routes"] == 1
    assert evidence["response_count"] == 1 and evidence["coder_count"] == 1
    assert evidence["downgrade"] == "partial_coder"
    assert evidence["consensus_confidence"] == "high"
    assert schema.is_valid(record)


def test_resume_skips_re_dispatch_for_an_existing_record(tmp_path):
    first = _run(tmp_path, dispatch=_dispatch_returning(_capture()))
    assert first["status"] == "ok"

    async def exploding_dispatch(**kwargs):  # pragma: no cover - must never run
        raise AssertionError("completed unit must not re-dispatch")

    second = _run(tmp_path, dispatch=exploding_dispatch)
    assert second == first
    assert len(list((tmp_path / "records").glob("*.json"))) == 1


def test_record_identity_follows_the_unit_not_the_cli_phase(tmp_path):
    # A wave's CLI --phase is only a default: a manifest unit carries its own phase,
    # and the record identity (phase + record_id) must follow the unit so the file
    # name, ledger call id, and record_id all agree (resume keys on the file stem).
    unit = _unit(
        unit_id="B1-T3-canonical-s1-seed0-r0-pi-self_moa", phase="B1",
        repeat=0, moa_mode="self_moa",
    )
    capture = _capture(
        endpoint_ids=("pi-deepseek-default",) * 3,
        route_evidence=tuple({"endpoint_id": "pi-deepseek-default"} for _ in range(3)),
        raw_method="self_moa",
    )
    record = _run(
        tmp_path, unit=unit, dispatch=_dispatch_returning(capture),
        config=_config(tmp_path, phase="B2"),  # CLI phase disagrees with the unit
    )
    assert record["phase"] == "B1"
    assert record["record_id"] == unit.unit_id
    assert schema.is_valid(record)
    assert (tmp_path / "records" / f"{unit.unit_id}.json").is_file()
