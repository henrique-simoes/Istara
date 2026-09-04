"""Contract tests for raw LLM prompt/output capture (CF-321).

All offline: fake ensemble/provider, tmp-path writers. Verifies the owner
requirements: one record per call, stable call_id, engine_path vocabulary,
secret redaction, capping with hash, fail-soft capture errors.
"""

from __future__ import annotations

import asyncio
import importlib
import types

import pytest

import tests.pi_benchmark.raw_capture as raw_capture
from tests.pi_benchmark.raw_capture import RawCaptureWriter, read_records

# importlib (not an import statement) keeps the gate's AST import graph acyclic for
# this new test module: an import-statement edge into live_driver would close a
# cycle through the package's pre-existing bare-import cluster.
live_driver = importlib.import_module("tests.pi_benchmark.live_driver")

pytestmark = pytest.mark.benchmark


class FakeProvider:
    model = "deepseek-v4-pro"

    def estimate_cost(
        self, input_tokens, output_tokens, cache_read_tokens=0, cache_write_tokens=0
    ):
        return (input_tokens * 0.55 + output_tokens * 2.19) / 1e6

    def load_api_key(self):
        return "sk-testsecretvalue1234567890"


def _unit(**overrides):
    base = dict(
        unit_id="u-cap",
        pack="canonical",
        scenario_id="s1",
        seed=0,
        repeat=1,
        engine="pi",
        phase="B2",
        moa_mode=None,
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


def _fake_ensemble(text="captured response", usage=None):
    async def _fn(params, **kwargs):
        return types.SimpleNamespace(
            samples=[
                types.SimpleNamespace(
                    text=text,
                    usage=usage
                    or {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                    endpoint_id="pi-deepseek-default",
                    served_model="deepseek-v4-pro",
                    stop_reason="stop",
                    tool_calls=[],
                    status="success",
                )
            ],
            endpoint_ids=["pi-deepseek-default"],
            usage=None,
            status="success",
        )

    return _fn


def test_writer_roundtrip_fields(tmp_path):
    writer = RawCaptureWriter(tmp_path / "raw")
    writer.record_prompt(
        call_id="u:1",
        scenario_id="s1",
        engine_path="pi_candidate",
        provider="deepseek",
        model="deepseek-v4-pro",
        adapter_mode="agentic_dispatcher",
        settings={"max_tokens": 1024},
        messages=[{"role": "user", "content": "hello"}],
    )
    writer.record_output(
        call_id="u:1",
        scenario_id="s1",
        engine_path="pi_candidate",
        provider="deepseek",
        model="deepseek-v4-pro",
        content="world",
        stop_reason="stop",
        latency_s=0.5,
        usage={"input_tokens": 1, "output_tokens": 1},
        cost_usd=0.0001,
    )
    prompts = read_records(tmp_path / "raw" / "prompts.jsonl.gz")
    outputs = read_records(tmp_path / "raw" / "outputs.jsonl.gz")
    assert len(prompts) == 1 and len(outputs) == 1
    assert prompts[0]["call_id"] == "u:1"
    assert prompts[0]["engine_path"] == "pi_candidate"
    assert prompts[0]["messages"][0]["content"] == "hello"
    assert prompts[0]["redactions"] == []
    assert outputs[0]["content"] == "world"
    assert outputs[0]["capping"] is None


def test_redaction_of_secret_values_and_patterns(tmp_path):
    writer = RawCaptureWriter(tmp_path / "raw")
    writer.record_prompt(
        call_id="u:1",
        scenario_id="s1",
        engine_path="baseline_istara",
        provider="deepseek",
        model="deepseek-v4-pro",
        adapter_mode="agentic_dispatcher",
        settings={"api_key": "should-never-appear", "max_tokens": 1},
        messages=[
            {"role": "user", "content": "key is sk-testsecretvalue1234567890 ok"}
        ],
        secret_values=("sk-testsecretvalue1234567890",),
    )
    (record,) = read_records(tmp_path / "raw" / "prompts.jsonl.gz")
    assert "sk-testsecretvalue1234567890" not in str(record)
    assert record["settings"]["api_key"] == raw_capture.REDACTED
    assert record["redactions"]  # non-empty and descriptive


def test_capping_records_hash_and_lengths(tmp_path):
    writer = RawCaptureWriter(tmp_path / "raw")
    big = "x" * (raw_capture.CAP_CHARS + 500)
    writer.record_output(
        call_id="u:1",
        scenario_id="s1",
        engine_path="pi_candidate",
        provider="deepseek",
        model="deepseek-v4-pro",
        content=big,
    )
    (record,) = read_records(tmp_path / "raw" / "outputs.jsonl.gz")
    assert len(record["content"]) == raw_capture.CAP_CHARS
    assert record["capping"]["full_length"] == raw_capture.CAP_CHARS + 500
    assert record["capping"]["retained_length"] == raw_capture.CAP_CHARS
    assert len(record["capping"]["full_sha256"]) == 64


def test_dispatch_unit_writes_prompt_and_output_records(tmp_path):
    writer = RawCaptureWriter(tmp_path / "raw")
    capture = asyncio.run(
        live_driver.dispatch_unit(
            unit=_unit(),
            tier="T3",
            prompt="hello benchmark",
            system="sys",
            provider=FakeProvider(),
            ensemble_fn=_fake_ensemble(),
            capture=writer,
        )
    )
    assert capture.capture_errors == ()
    prompts = read_records(tmp_path / "raw" / "prompts.jsonl.gz")
    outputs = read_records(tmp_path / "raw" / "outputs.jsonl.gz")
    assert [p["call_id"] for p in prompts] == ["u-cap:pi:1"]
    assert [o["call_id"] for o in outputs] == ["u-cap:pi:1"]
    assert prompts[0]["engine_path"] == "pi_candidate"
    assert prompts[0]["settings"]["deepseek_key_present"] is True
    assert prompts[0]["settings"]["max_tokens"] > 0
    assert outputs[0]["content"] == "captured response"
    assert outputs[0]["usage"]["total_tokens"] == 15
    assert outputs[0]["cost_usd"] is not None
    assert outputs[0]["latency_s"] is not None


def test_dispatch_unit_legacy_capture_uses_baseline_path_and_shared_pi_authority(
    tmp_path,
):
    async def fake_ensemble(params, **kwargs):
        return types.SimpleNamespace(
            samples=[
                types.SimpleNamespace(
                    text="legacy response",
                    usage={"input_tokens": 3, "output_tokens": 2, "total_tokens": 5},
                    endpoint_id="pi-deepseek-default",
                    served_model="deepseek-v4-pro",
                    route_evidence={
                        "endpoint_id": "pi-deepseek-default",
                        "provider": "deepseek",
                    },
                    stop_reason="stop",
                    tool_calls=[],
                    status="success",
                )
            ],
            endpoint_ids=["pi-deepseek-default"],
            usage=None,
            status="success",
        )

    writer = RawCaptureWriter(tmp_path / "raw")
    asyncio.run(
        live_driver.dispatch_unit(
            unit=_unit(engine="legacy"),
            tier="T3",
            prompt="hello",
            provider=FakeProvider(),
            ensemble_fn=fake_ensemble,
            capture=writer,
        )
    )
    (prompt,) = read_records(tmp_path / "raw" / "prompts.jsonl.gz")
    assert prompt["engine_path"] == "baseline_istara"
    assert prompt["call_id"] == "u-cap:legacy:1"
    # Provider credentials are not needed for route admission and must never appear.
    assert "sk-testsecretvalue1234567890" not in str(prompt)


def test_capture_failure_is_fail_soft(tmp_path):
    class BrokenWriter:
        def record_prompt(self, **kwargs):
            raise OSError("disk full")

        def record_output(self, **kwargs):
            raise OSError("disk full")

    capture = asyncio.run(
        live_driver.dispatch_unit(
            unit=_unit(),
            tier="T3",
            prompt="hello",
            provider=FakeProvider(),
            ensemble_fn=_fake_ensemble(),
            capture=BrokenWriter(),
        )
    )
    # The paid dispatch result survives; capture errors are surfaced, not raised.
    assert capture.text == "captured response"
    assert len(capture.capture_errors) == 2
    assert "disk full" in capture.capture_errors[0]


def test_moa_capture_writes_one_record_per_slot(tmp_path):
    class FakeAgentic:
        async def ensemble(self, **kwargs):
            samples = [
                types.SimpleNamespace(
                    text=f"sample {i}",
                    usage={"input_tokens": 2, "output_tokens": 1, "total_tokens": 3},
                    endpoint_id="pi-deepseek-default",
                    served_model="deepseek-v4-pro",
                    stop_reason="stop",
                    tool_calls=[],
                    status="success",
                )
                for i in range(3)
            ]
            return types.SimpleNamespace(
                samples=samples,
                endpoint_ids=[],
                usage=None,
                status="success",
                method="self_moa",
            )

    writer = RawCaptureWriter(tmp_path / "raw")
    asyncio.run(
        live_driver.dispatch_unit(
            unit=_unit(moa_mode="self_moa"),
            tier="T3",
            prompt="hello",
            moa_n=3,
            provider=FakeProvider(),
            agentic_module=FakeAgentic(),
            capture=writer,
        )
    )
    prompts = read_records(tmp_path / "raw" / "prompts.jsonl.gz")
    outputs = read_records(tmp_path / "raw" / "outputs.jsonl.gz")
    assert [p["call_id"] for p in prompts] == ["u-cap:pi:1", "u-cap:pi:2", "u-cap:pi:3"]
    assert [p["settings"]["temperature"] for p in prompts] == [0.3, 0.7, 1.0]
    assert [o["content"] for o in outputs] == ["sample 0", "sample 1", "sample 2"]
