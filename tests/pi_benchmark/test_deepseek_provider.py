"""Contract tests for the DeepSeek-only provider adapter (B0 scheduling).

Every test uses injected fakes: no real network, no real keychain, no real key.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from tests.pi_benchmark.budget_ledger import BudgetExceeded, BudgetLedger
from tests.pi_benchmark.deepseek_provider import (
    DEEPSEEK_BASE_URL,
    DeepSeekProvider,
    ProviderCallFailed,
    ProviderRejected,
    ProviderUsage,
)

pytestmark = pytest.mark.benchmark

SENTINEL_KEY = "sk-SENTINEL-SECRET-9f8e7d6c5b"  # fake; asserted absent from all output


def _provider(**overrides) -> DeepSeekProvider:
    base = dict(provider="deepseek", model="deepseek-v4-pro", key_loader=lambda: SENTINEL_KEY)
    base.update(overrides)
    return DeepSeekProvider(**base)


def _usage_payload(**usage_overrides) -> dict:
    usage = {
        "prompt_tokens": 1000,
        "completion_tokens": 500,
        "prompt_cache_hit_tokens": 100,
        "prompt_cache_miss_tokens": 900,
    }
    usage.update(usage_overrides)
    return {"choices": [{"message": {"content": "ok"}}], "usage": usage}


def test_provider_rejection_battery():
    for provider in ("claude", "openai", "ollama", "lm-studio", "petals", "kimi"):
        with pytest.raises(ProviderRejected):
            DeepSeekProvider(provider=provider, model="deepseek-v4-pro")
    for model in ("deepseek-chat", "gpt-5", "deepseek-v3", "claude-opus-4-8"):
        with pytest.raises(ProviderRejected):
            DeepSeekProvider(provider="deepseek", model=model)
    # The single approved pair is accepted.
    _provider()


def test_estimate_cost_exact_arithmetic():
    provider = _provider()
    assert provider.estimate_cost(1_000_000, 1_000_000) == 2.74  # 0.55 + 2.19
    assert provider.estimate_cost(0, 0, 1_000_000, 1_000_000) == 0.69  # 0.14 + 0.55
    # (1000*0.55 + 500*2.19) / 1e6 = 0.0016450
    assert provider.estimate_cost(1000, 500) == 0.001645
    assert provider.estimate_cost(0, 0) == 0.0


def test_chat_happy_path_commits_actual_cost(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)
    provider = _provider(http_post=lambda url, headers, body, timeout: _usage_payload())
    text, usage = provider.chat(
        messages=[{"role": "user", "content": "judge this"}],
        max_tokens=512,
        ledger=ledger,
        call_id="judge-1",
    )
    assert text == "ok"
    assert usage == ProviderUsage(
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=100,
        cache_write_tokens=900,
        total_tokens=1500,
        cost_usd=0.002154,  # 0.001645 + 100*0.14/1e6 + 900*0.55/1e6
        estimate=False,
    )
    rows = [json.loads(line) for line in ledger.path.read_text().splitlines()]
    assert [row["type"] for row in rows] == ["reserve", "commit"]
    assert rows[0]["call_id"] == rows[1]["call_id"] == "judge-1"
    assert rows[0]["kind"] == "judge"
    assert rows[1]["actual_cost_usd"] == 0.002154
    assert ledger.spent_usd() == 0.002154
    assert ledger.outstanding() == {}


def test_unknown_usage_fails_closed_and_keeps_reservation(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)
    provider = _provider(
        http_post=lambda url, headers, body, timeout: {
            "choices": [{"message": {"content": "ok"}}]
        }  # no "usage" block
    )
    with pytest.raises(ProviderCallFailed, match="unknown_usage"):
        provider.chat(
            messages=[{"role": "user", "content": "judge"}],
            max_tokens=512,
            ledger=ledger,
            call_id="judge-unknown",
        )
    # Fail closed: the worst-case reservation is NOT released.
    assert list(ledger.outstanding()) == ["judge-unknown"]
    assert [json.loads(line)["type"] for line in ledger.path.read_text().splitlines()] == ["reserve"]


def test_missing_key_is_pre_dispatch_and_releases(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)
    provider = _provider(
        key_loader=lambda: None,
        http_post=lambda *args: pytest.fail("http_post must not run without a key"),
    )
    with pytest.raises(ProviderCallFailed, match="missing_api_key"):
        provider.chat(
            messages=[{"role": "user", "content": "judge"}],
            max_tokens=512,
            ledger=ledger,
            call_id="judge-no-key",
        )
    assert ledger.outstanding() == {}
    assert [json.loads(line)["type"] for line in ledger.path.read_text().splitlines()] == [
        "reserve",
        "release",
    ]


def test_budget_exceeded_propagates_and_never_dispatches(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=0.0001)
    provider = _provider(
        http_post=lambda *args: pytest.fail("http_post must not run when the cap is blown"),
    )
    with pytest.raises(BudgetExceeded):
        provider.chat(
            messages=[{"role": "user", "content": "x" * 4000}],
            max_tokens=512,
            ledger=ledger,
            call_id="judge-over-budget",
        )
    assert not ledger.path.exists()  # the refused reserve appended nothing


def test_key_never_leaks_to_exceptions_or_ledger(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)

    def boom(url, headers, body, timeout):
        # The transport saw the key (it must, to authenticate)...
        assert headers["Authorization"] == f"Bearer {SENTINEL_KEY}"
        raise ConnectionError("connection refused by 10.0.0.1:443")

    provider = _provider(http_post=boom)
    with pytest.raises(ProviderCallFailed) as excinfo:
        provider.chat(
            messages=[{"role": "user", "content": "judge"}],
            max_tokens=512,
            ledger=ledger,
            call_id="judge-leak-check",
        )
    # ...but the key appears in neither the exception chain nor the ledger file.
    assert SENTINEL_KEY not in str(excinfo.value)
    assert SENTINEL_KEY not in str(excinfo.value.__cause__)
    assert SENTINEL_KEY not in ledger.path.read_text()

    missing = _provider(key_loader=lambda: None)
    with pytest.raises(ProviderCallFailed) as missing_exc:
        missing.load_api_key()
    assert "missing_api_key" in str(missing_exc.value)


def test_endpoint_fingerprint_is_redacted():
    provider = _provider()
    fingerprint = provider.endpoint_fingerprint()
    expected = "deepseek:" + hashlib.sha256(DEEPSEEK_BASE_URL.encode()).hexdigest()[:12]
    assert fingerprint == expected
    assert fingerprint.startswith("deepseek:") and len(fingerprint) == len("deepseek:") + 12
    assert DEEPSEEK_BASE_URL not in fingerprint
    assert SENTINEL_KEY not in fingerprint


def test_preflight_is_a_minimal_ledgered_call(tmp_path):
    ledger = BudgetLedger(tmp_path / "ledger.jsonl", cap_usd=1.00)
    seen: dict = {}

    def fake_post(url, headers, body, timeout):
        seen["body"] = body
        return _usage_payload(prompt_tokens=2, completion_tokens=1)

    provider = _provider(http_post=fake_post)
    usage = provider.preflight(ledger=ledger)
    assert seen["body"]["messages"] == [{"role": "user", "content": "ping"}]
    assert seen["body"]["max_tokens"] == 1
    assert usage.estimate is False
    rows = [json.loads(line) for line in ledger.path.read_text().splitlines()]
    assert [row["type"] for row in rows] == ["reserve", "commit"]
    assert rows[0]["kind"] == "preflight"
    assert rows[0]["call_id"] == "preflight"
