"""DeepSeek-only provider adapter for judge/preflight calls (B0 scheduling).

The "B0 offline scheduling + B1..B_N process waves" plan permits exactly one live
provider: DeepSeek ``deepseek-v4-pro``, under the $1.00 cumulative cap enforced by
:mod:`tests.pi_benchmark.budget_ledger`. This adapter is the provider-isolation
gate: any other provider or model string is rejected at construction, before any
dispatch is possible. The DUT path lives elsewhere — this adapter serves judge and
preflight calls only.

Budget discipline: ``chat`` reserves worst-case cost in the ledger *before*
dispatch, commits provider-reported actual cost on success, releases the
reservation only for pre-dispatch failures (e.g. a missing API key), and — fail
closed — retains the reservation as worst-case spend whenever a dispatched call
fails or returns unknown usage.

Secret discipline: the API key is held in memory only. It is never written to
files, logs, ledger rows, or exception messages (not even a prefix).

Import-safe at T0: importing this module touches no network, keychain, backend, or
model (``urllib`` is imported lazily inside the default HTTP transport).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from dataclasses import dataclass
from typing import Callable

from tests.pi_benchmark.budget_ledger import (
    DEEPSEEK_PRICING,
    BudgetLedger,
    LedgerStateError,
    Pricing,
)

DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-pro"
KEYCHAIN_SERVICE = "istara-pi-deepseek"
KEYCHAIN_ACCOUNT = "openclaw"
ENV_SECRET_NAME = "ISTARA_PI_SECRET_PI_DEEPSEEK_DEFAULT"

_REQUEST_TIMEOUT_S = 60.0

# Worst-case input-token floor for a reservation. Even a tiny prompt books at least this
# many input-priced tokens so a real call's provider-reported usage — which can exceed a
# naive chars/4 estimate, including cache-class tokens — stays within the reservation the
# ledger will accept at commit time. See ``chat`` for the full formula.
MIN_RESERVE_INPUT_TOKENS = 256


class ProviderRejected(ValueError):
    """Raised when a non-DeepSeek provider or non-approved model is requested."""


class ProviderCallFailed(RuntimeError):
    """Raised when a provider call cannot be completed or accounted for."""


@dataclass(frozen=True)
class ProviderUsage:
    """Token usage and cost for one provider call.

    ``estimate`` is False when the numbers are provider-reported, True when they
    were estimated locally (worst case).
    """

    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    total_tokens: int
    cost_usd: float
    estimate: bool  # False = provider-reported usage; True = locally estimated


def _urllib_http_post(url: str, headers: dict, body: dict, timeout: float) -> dict:
    """Default HTTP transport: one JSON POST via urllib, parsed JSON response."""
    import urllib.request

    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _require_int(usage: dict, key: str, default: int | None = None) -> int:
    value = usage.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise ProviderCallFailed("unknown_usage")
    return value


class DeepSeekProvider:
    """Provider-isolated client for DeepSeek ``deepseek-v4-pro`` judge calls."""

    def __init__(
        self,
        *,
        provider: str,
        model: str,
        base_url: str = DEEPSEEK_BASE_URL,
        pricing: Pricing = DEEPSEEK_PRICING,
        key_loader: Callable[[], str | None] | None = None,
        http_post: Callable[[str, dict, dict, float], dict] | None = None,
    ) -> None:
        # Provider-isolation gate: anything but the single approved provider+model
        # is refused here, before any key load or dispatch can happen.
        if provider != "deepseek" or model != DEEPSEEK_MODEL:
            raise ProviderRejected(
                f"provider/model rejected: {provider!r}/{model!r}; "
                f"only 'deepseek'/'{DEEPSEEK_MODEL}' is permitted for this benchmark"
            )
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.pricing = pricing
        self._key_loader = key_loader
        self._http_post = http_post or _urllib_http_post

    # -- cost accounting --------------------------------------------------------

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> float:
        """Exact cost in USD from the pricing table, rounded to 7 decimals."""
        cost = (
            input_tokens * self.pricing.input_per_million
            + output_tokens * self.pricing.output_per_million
            + cache_read_tokens * self.pricing.cache_read_per_million
            + cache_write_tokens * self.pricing.cache_write_per_million
        ) / 1_000_000
        return round(cost, 7)

    # -- credentials --------------------------------------------------------------

    def load_api_key(self) -> str:
        """Resolve the API key: injected loader, else env var, else macOS Keychain.

        The key is held in memory only and never appears in files, logs, ledger
        rows, or exception messages. Raises ProviderCallFailed("missing_api_key")
        when no source yields a key.
        """
        key: str | None = None
        if self._key_loader is not None:
            key = self._key_loader()
        else:
            key = os.environ.get(ENV_SECRET_NAME)
            if not key:
                try:
                    result = subprocess.run(
                        [
                            "security",
                            "find-generic-password",
                            "-a",
                            KEYCHAIN_ACCOUNT,
                            "-s",
                            KEYCHAIN_SERVICE,
                            "-w",
                        ],
                        capture_output=True,  # stderr suppressed: never echoed to logs
                        text=True,
                        check=False,
                    )
                except OSError:
                    result = None
                if result is not None and result.returncode == 0:
                    key = result.stdout.strip()
        if not key:
            raise ProviderCallFailed("missing_api_key")
        return key

    def endpoint_fingerprint(self) -> str:
        """Redacted endpoint identifier; contains no key and no credential material."""
        digest = hashlib.sha256(self.base_url.encode("utf-8")).hexdigest()[:12]
        return f"deepseek:{digest}"

    # -- calls ---------------------------------------------------------------------

    def chat(
        self,
        *,
        messages: list[dict],
        temperature: float = 0.0,
        max_tokens: int = 512,
        ledger: BudgetLedger | None = None,
        call_id: str,
        kind: str = "judge",
        estimated_input_tokens: int | None = None,
    ) -> tuple[str, ProviderUsage]:
        """One chat completion, budget-ledgered end to end.

        Reserves worst-case cost before dispatch; commits provider-reported actual
        cost on success. Missing/invalid usage raises
        ProviderCallFailed("unknown_usage") and the reservation is RETAINED (fail
        closed). Network/HTTP failures after dispatch likewise retain the
        reservation. Only pre-dispatch failures (e.g. missing API key) release it.
        """
        if estimated_input_tokens is None:
            estimated_input_tokens = math.ceil(len(json.dumps(messages)) / 4)
        # Reserve a margin of input-priced tokens — 2x the estimate, floored at
        # MIN_RESERVE_INPUT_TOKENS — plus the full max_tokens output bound. The 2x covers
        # tokenizer variance and the worst-case cache-miss token double-count; the floor
        # covers tiny prompts. Under-reserving is unsafe: the ledger refuses a commit whose
        # actual cost exceeds its reservation, so a too-tight reservation would turn a
        # normal call into a post-dispatch LedgerStateError.
        reserve_input_tokens = max(2 * estimated_input_tokens, MIN_RESERVE_INPUT_TOKENS)
        worst_case = self.estimate_cost(reserve_input_tokens, max_tokens)
        if ledger is not None:
            ledger.reserve(call_id, worst_case, kind=kind)

        try:
            key = self.load_api_key()
        except ProviderCallFailed:
            # Pre-dispatch failure: no provider usage could exist, so the
            # reservation is safe to release.
            if ledger is not None:
                ledger.release(call_id, reason="missing_api_key")
            raise

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        try:
            payload = self._http_post(url, headers, body, _REQUEST_TIMEOUT_S)
        except Exception as exc:
            # Dispatched but failed: the reservation stays booked (fail closed).
            # The exception text names only the error type — never the key or body.
            raise ProviderCallFailed(f"dispatch_failed:{type(exc).__name__}") from exc

        try:
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderCallFailed("malformed_response") from exc

        usage_raw = payload.get("usage")
        if not isinstance(usage_raw, dict):
            # Unknown usage after dispatch: do NOT release — worst case stays booked.
            raise ProviderCallFailed("unknown_usage")
        input_tokens = _require_int(usage_raw, "prompt_tokens")
        output_tokens = _require_int(usage_raw, "completion_tokens")
        cache_read_tokens = _require_int(usage_raw, "prompt_cache_hit_tokens", 0)
        cache_write_tokens = _require_int(usage_raw, "prompt_cache_miss_tokens", 0)
        actual_cost = self.estimate_cost(
            input_tokens, output_tokens, cache_read_tokens, cache_write_tokens
        )
        usage = ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cache_read_tokens=cache_read_tokens,
            cache_write_tokens=cache_write_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=actual_cost,
            estimate=False,
        )
        if ledger is not None:
            try:
                ledger.commit(
                    call_id,
                    actual_cost,
                    usage={
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_read_tokens": cache_read_tokens,
                        "cache_write_tokens": cache_write_tokens,
                        "total_tokens": usage.total_tokens,
                    },
                )
            except LedgerStateError as exc:
                # Actual provider cost exceeded the worst-case reservation. The commit
                # appended nothing, so the reservation stays booked as worst-case spend
                # (fail closed); surface a typed failure rather than letting the ledger
                # state error escape uncaught.
                raise ProviderCallFailed("over_reservation_fail_closed") from exc
        return content, usage

    def preflight(
        self,
        *,
        ledger: BudgetLedger | None = None,
        call_id: str = "preflight",
    ) -> ProviderUsage:
        """Single cheapest-possible live call proving key, endpoint, and accounting."""
        _, usage = self.chat(
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
            ledger=ledger,
            call_id=call_id,
            kind="preflight",
        )
        return usage
