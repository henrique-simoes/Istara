"""Tests for the versioned Istara AI eval runner."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from scripts import run_istara_evals as runner


def test_eval_registry_and_case_files_are_well_formed():
    registry = runner.read_json(runner.DEFAULT_REGISTRY)
    cases = runner.read_json(runner.DEFAULT_CASES)

    suite_ids = {suite["id"] for suite in registry["suites"]}
    assert registry["schema_version"] == 1
    assert registry["default_model"] == "google/gemma-4-e4b"
    assert {
        "classic_llm",
        "rag",
        "prompt_rag",
        "llmlingua",
        "dag_react",
        "memory_reasoning_bank",
        "memento_skills",
        "meta_hyperagent",
        "thinking_output",
        "voice_transcription",
    } <= suite_ids
    assert cases["live_cases"]
    assert cases["static_cases"]
    assert all(case["suite"] in suite_ids for case in cases["live_cases"])
    assert all(case["suite"] in suite_ids for case in cases["static_cases"])


def test_manifest_does_not_expose_live_endpoint_or_token(tmp_path, monkeypatch):
    private_url = "http://192.0.2.142:1234"
    private_token = "live-test-token-never-write"
    monkeypatch.setenv("ISTARA_LIVE_LLM_BASE_URL", private_url)
    monkeypatch.setenv("ISTARA_LIVE_LLM_API_KEY", private_token)

    config = runner.EvalConfig(
        suite="static",
        registry_path=runner.DEFAULT_REGISTRY,
        cases_path=runner.DEFAULT_CASES,
        output_dir=tmp_path,
        require_live_llm=False,
        max_live_cases=None,
        timeout_seconds=1.0,
        fail_on_threshold=False,
        compass_spec="CF-SPEC-26",
        compass_task="CF-295",
    )
    manifest = runner.build_manifest(
        config=config,
        registry=runner.read_json(runner.DEFAULT_REGISTRY),
        cases=runner.read_json(runner.DEFAULT_CASES),
        output_dir=tmp_path,
        loaded_env_files=0,
    )
    serialized = json.dumps(manifest, sort_keys=True)

    assert private_url not in serialized
    assert private_token not in serialized
    assert "192.0.2.142" not in serialized
    assert manifest["live_llm"]["base_url_configured"] is True
    assert manifest["live_llm"]["api_key_configured"] is True
    assert manifest["live_llm"]["endpoint_fingerprint"]


def test_static_eval_run_writes_versioned_artifacts(tmp_path, monkeypatch):
    monkeypatch.delenv("ISTARA_LIVE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("ISTARA_LIVE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("ISTARA_LLM_TEST_API_KEY", raising=False)
    monkeypatch.delenv("ISTARA_PRIMARY_LLM_TEST_API_KEY", raising=False)
    monkeypatch.delenv("LMSTUDIO_API_KEY", raising=False)

    config = runner.EvalConfig(
        suite="static",
        registry_path=runner.DEFAULT_REGISTRY,
        cases_path=runner.DEFAULT_CASES,
        output_dir=tmp_path,
        require_live_llm=False,
        max_live_cases=None,
        timeout_seconds=1.0,
        fail_on_threshold=False,
        compass_spec="CF-SPEC-26",
        compass_task="CF-295",
        allow_unignored_output=True,
    )
    run = asyncio.run(runner.run_eval_suite(config))

    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "results.jsonl").exists()
    assert (tmp_path / "report.md").exists()
    assert run["summary"]["totals"]["total"] >= 8
    assert run["summary"]["totals"]["blocked"] == 0

    artifacts = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [
            tmp_path / "manifest.json",
            tmp_path / "summary.json",
            tmp_path / "results.jsonl",
            tmp_path / "report.md",
        ]
    )
    assert "10.0.10." not in artifacts
    assert "live-test-token" not in artifacts


def test_live_case_blocks_without_config(monkeypatch):
    monkeypatch.delenv("ISTARA_LIVE_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("ISTARA_PRIMARY_LLM_TEST_BASE_URL", raising=False)
    monkeypatch.delenv("ISTARA_LIVE_LLM_API_KEY", raising=False)
    monkeypatch.delenv("ISTARA_LLM_TEST_API_KEY", raising=False)
    monkeypatch.delenv("ISTARA_PRIMARY_LLM_TEST_API_KEY", raising=False)
    monkeypatch.delenv("LMSTUDIO_API_KEY", raising=False)

    case = runner.read_json(runner.DEFAULT_CASES)["live_cases"][0]
    result = asyncio.run(
        runner.run_live_case(
            case,
            timeout_seconds=0.1,
            require_live_llm=False,
        )
    )

    assert result["status"] == "blocked"
    assert result["score"] == 0.0


def test_live_cases_pin_thinking_mode_off_for_json_benchmarks():
    cases = runner.read_json(runner.DEFAULT_CASES)["live_cases"]

    assert all(case.get("thinking_mode") == "off" for case in cases)
    script = Path(runner.__file__).read_text(encoding="utf-8")
    assert "compute_registry.chat" in script
    assert "thinking_mode=case.get" in script


def test_live_case_uses_hardened_compute_registry_path(monkeypatch):
    monkeypatch.setenv("ISTARA_LIVE_LLM_BASE_URL", "http://192.0.2.142:1234")
    monkeypatch.setenv("ISTARA_LIVE_LLM_API_KEY", "private-test-token")

    from app.core.compute_registry import compute_registry

    original_nodes = dict(compute_registry._nodes)
    calls: dict[str, object] = {}

    async def fake_chat(messages, **kwargs):
        calls["messages"] = messages
        calls.update(kwargs)
        return {"message": {"role": "assistant", "content": "ok"}}

    monkeypatch.setattr(compute_registry, "chat", fake_chat)
    result = asyncio.run(
        runner.run_live_case(
            {
                "id": "live_hardened_path",
                "suite": "classic_llm",
                "messages": [{"role": "user", "content": "Reply with ok."}],
                "thinking_mode": "off",
                "max_tokens": 8,
                "checks": {"contains": ["ok"]},
            },
            timeout_seconds=1.0,
            require_live_llm=True,
        )
    )

    assert result["status"] == "passed"
    assert result["metrics"]["llm_serving_path"] == "compute_registry.chat"
    assert calls["model"] == "google/gemma-4-e4b"
    assert calls["thinking_mode"] == "off"
    assert compute_registry._nodes == original_nodes


def test_custom_eval_output_dir_is_guarded(tmp_path):
    config = runner.EvalConfig(
        suite="static",
        registry_path=runner.DEFAULT_REGISTRY,
        cases_path=runner.DEFAULT_CASES,
        output_dir=tmp_path,
        require_live_llm=False,
        max_live_cases=None,
        timeout_seconds=1.0,
        fail_on_threshold=False,
        compass_spec="CF-SPEC-26",
        compass_task="CF-295",
    )

    with pytest.raises(ValueError, match="tests/evals/.results"):
        runner.resolve_eval_output_dir(config, {"short_head": "abc123", "dirty": True})

    config.allow_unignored_output = True
    assert (
        runner.resolve_eval_output_dir(config, {"short_head": "abc123", "dirty": True})
        == tmp_path
    )


def test_dag_validator_rejects_cycles():
    payload = {
        "nodes": [{"id": "a"}, {"id": "b"}],
        "edges": [["a", "b"], ["b", "a"]],
    }

    valid, detail = runner.validate_dag_payload(payload)

    assert valid is False
    assert "cycle" in detail
