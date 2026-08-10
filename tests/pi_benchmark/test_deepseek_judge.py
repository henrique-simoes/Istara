"""Contract tests for the DeepSeek-backed judge_fn (Lane B). Pure tier-T0 fakes."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.pi_benchmark import deepseek_judge
from tests.pi_benchmark.deepseek_judge import make_deepseek_judge_fn, parse_verdict
from tests.pi_benchmark.judge import JudgeConfig, JudgeIsDutError, JudgeLayer

pytestmark = pytest.mark.benchmark

JUDGE_CONFIG_PATH = Path(__file__).with_name("judge_config.json")


class FakeProvider:
    """Records judge calls and returns a canned verdict text."""

    def __init__(self, response: str = '{"winner": "A", "score_a": 6, "score_b": 4}'):
        self.response = response
        self.calls: list[dict] = []

    def chat(self, *, messages, temperature, max_tokens, ledger, call_id, kind):
        self.calls.append({
            "messages": messages, "temperature": temperature, "max_tokens": max_tokens,
            "ledger": ledger, "call_id": call_id, "kind": kind,
        })
        return self.response


class FakeLedger:
    def __init__(self):
        self.entries: list[tuple] = []


def test_judge_fn_calls_provider_as_judge_on_the_shared_ledger():
    provider, ledger = FakeProvider(), FakeLedger()
    judge_fn = make_deepseek_judge_fn(provider=provider, ledger=ledger)
    verdict = judge_fn("PROMPT", {"A": "text-a", "B": "text-b"})

    assert verdict == {"winner": "A", "score_a": 6.0, "score_b": 4.0}
    assert len(provider.calls) == 1
    call = provider.calls[0]
    assert call["kind"] == "judge"
    assert call["ledger"] is ledger            # same ledger/cap as benchmark calls
    assert call["temperature"] == 0.0
    assert call["max_tokens"] == 512
    assert call["call_id"].startswith("judge-") and len(call["call_id"]) == len("judge-") + 16
    content = call["messages"][0]["content"]
    assert content.startswith("PROMPT") and "Respond with JSON" in content


def test_verdict_json_wrapped_in_prose_is_parsed():
    provider = FakeProvider('Sure! The verdict is {"winner":"B","score_a":3,"score_b":5} — hope that helps.')
    judge_fn = make_deepseek_judge_fn(provider=provider, ledger=None)
    assert judge_fn("p", {"A": "a", "B": "b"}) == {"winner": "B", "score_a": 3.0, "score_b": 5.0}


def test_tie_verdict_normalises_to_lowercase():
    assert parse_verdict('{"winner":"tie","score_a":4,"score_b":4}') == {
        "winner": "tie", "score_a": 4.0, "score_b": 4.0,
    }


def test_provider_chat_tuple_return_is_unpacked():
    """The real DeepSeekProvider.chat returns (content, usage) — the judge must unpack it."""

    class TupleProvider:
        def chat(self, **_kwargs):
            return '{"winner":"B","score_a":2,"score_b":6}', object()

    judge_fn = make_deepseek_judge_fn(provider=TupleProvider(), ledger=None)
    assert judge_fn("p", {"A": "a", "B": "b"}) == {"winner": "B", "score_a": 2.0, "score_b": 6.0}


@pytest.mark.parametrize("bad", [
    "no json here at all",
    '{"winner":"X","score_a":1,"score_b":2}',   # invalid winner
    '{"winner":"A","score_a":"high"}',           # non-numeric / missing scores
    "{not json}",
])
def test_malformed_verdict_raises_never_a_silent_tie(bad):
    provider = FakeProvider(bad)
    judge_fn = make_deepseek_judge_fn(provider=provider, ledger=None)
    with pytest.raises(deepseek_judge.ProviderCallFailed):
        judge_fn("p", {"A": "a", "B": "b"})


def test_judge_config_rejects_dut_overlap_by_default():
    with pytest.raises(JudgeIsDutError):
        JudgeConfig.from_dict({"judge_model": "m", "dut_models": ["m"]})


def test_judge_config_allow_dut_model_permits_role_separated_overlap():
    config = JudgeConfig.from_dict({"judge_model": "m", "dut_models": ["m"], "allow_dut_model": True})
    assert config.allow_dut_model is True
    assert config.judge_model == "m"


def test_shipped_judge_config_loads_the_deepseek_only_policy():
    config = JudgeConfig.load(JUDGE_CONFIG_PATH)
    assert config.judge_model == "deepseek-v4-pro"
    assert "deepseek-v4-pro" in config.dut_models
    assert config.allow_dut_model is True
    raw = json.loads(JUDGE_CONFIG_PATH.read_text(encoding="utf-8"))
    assert "role" in raw["separation_note"] and "ledger" in raw["separation_note"]


def test_judge_layer_end_to_end_with_the_deepseek_judge_fn():
    config = JudgeConfig.from_dict({
        "judge_model": "deepseek-v4-pro", "dut_models": ["deepseek-v4-pro"],
        "allow_dut_model": True,
    })
    provider = FakeProvider('{"winner":"A","score_a":6,"score_b":4}')
    layer = JudgeLayer(config, judge_fn=make_deepseek_judge_fn(provider=provider, ledger=None))
    judgment = layer.judge(
        scenario_id="s", run_id="r", axis="output_quality",
        pi_output="PI-TEXT", legacy_output="LEGACY-TEXT",
    )
    # Winner was un-blinded to a real engine; scores follow the position map.
    assert judgment.winner in ("pi", "legacy")
    assert judgment.scores[judgment.winner] == 6.0
    assert len(provider.calls) == 1
    # Cache still prevents duplicate spend on a repeated judgment.
    layer.judge(scenario_id="s", run_id="r", axis="output_quality",
                pi_output="PI-TEXT", legacy_output="LEGACY-TEXT")
    assert len(provider.calls) == 1
