"""Contract tests for the JudgeLayer (task B0-7). Pure tier-T0 with a fake judge_fn."""

from __future__ import annotations

import pytest

from tests.pi_benchmark.judge import (
    JudgeConfig,
    JudgeIsDutError,
    JudgeLayer,
)

pytestmark = pytest.mark.benchmark


def _config(**overrides) -> JudgeConfig:
    data = {"judge_model": "judge-x", "dut_models": ["pi-model", "legacy-model"]}
    data.update(overrides)
    return JudgeConfig.from_dict(data)


def test_judge_must_not_be_a_dut():
    with pytest.raises(JudgeIsDutError):
        _config(judge_model="pi-model")


def test_blind_prompt_hides_engine_labels_and_swap_is_deterministic():
    layer = JudgeLayer(
        _config(),
        judge_fn=lambda prompt, arms: {"winner": "A", "score_a": 6, "score_b": 4},
    )
    # Same pair key → same swap decision every time (reproducible blinding).
    a = layer._blind("s|r|output_quality", "PI-TEXT", "LEGACY-TEXT")
    b = layer._blind("s|r|output_quality", "PI-TEXT", "LEGACY-TEXT")
    assert a == b
    arms, position = a
    assert set(position.values()) == {"pi", "legacy"}
    # Blind slot labels (A/B) carry no engine identity.
    assert set(arms) == {"A", "B"}


def test_verdict_is_unblinded_to_the_real_engine():
    calls = []

    def judge_fn(prompt, arms):
        calls.append(prompt)
        # Always vote for whichever slot holds PI-TEXT, regardless of position.
        winner = "A" if arms["A"] == "PI-TEXT" else "B"
        return {"winner": winner, "score_a": 7, "score_b": 3}

    layer = JudgeLayer(_config(), judge_fn=judge_fn)
    j = layer.judge(
        scenario_id="s",
        run_id="r",
        axis="output_quality",
        pi_output="PI-TEXT",
        legacy_output="LEGACY-TEXT",
    )
    assert j.winner == "pi"
    assert j.scores["pi"] == 7.0 and j.scores["legacy"] == 3.0
    assert len(j.prompt_sha256) == 64
    assert len(calls) == 1


def test_cache_prevents_respend():
    invocations = {"n": 0}

    def judge_fn(prompt, arms):
        invocations["n"] += 1
        return {"winner": "tie", "score_a": 5, "score_b": 5}

    layer = JudgeLayer(_config(), judge_fn=judge_fn)
    first = layer.judge(
        scenario_id="s",
        run_id="r",
        axis="output_quality",
        pi_output="a",
        legacy_output="b",
    )
    second = layer.judge(
        scenario_id="s",
        run_id="r",
        axis="output_quality",
        pi_output="a",
        legacy_output="b",
    )
    assert invocations["n"] == 1  # second call served from cache (B4 re-report is free)
    assert first.prompt_sha256 == second.prompt_sha256
    assert second.cached is True


def test_missing_judge_fn_refuses_rather_than_fabricates():
    layer = JudgeLayer(_config())  # no judge_fn (live judging is gated)
    with pytest.raises(RuntimeError):
        layer.judge(
            scenario_id="s",
            run_id="r",
            axis="output_quality",
            pi_output="a",
            legacy_output="b",
        )


def test_rubric_version_override_from_config():
    layer = JudgeLayer(_config(rubric_versions={"output_quality": "9.9.9"}))
    assert layer.rubric_for("output_quality").version == "9.9.9"
