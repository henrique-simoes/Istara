"""DeepSeek-backed judge_fn for the JudgeLayer (Lane B).

Under the DeepSeek-only policy the judge IS the DUT model (``deepseek-v4-pro``) but never
the DUT *role*: separation is enforced by purpose (``kind="judge"`` calls, pinned judge
endpoint), the JudgeLayer's blind A/B relabelling and deterministic position swap, and a
shared budget ledger so judge spend and benchmark spend draw from the same owner-approved
cap. See ``judge_config.json``'s ``separation_note`` and :class:`judge.JudgeConfig`'s
``allow_dut_model`` docstring.

The returned ``judge_fn`` matches :data:`judge.JudgeFn`: ``(prompt, arms) -> dict`` with
``{"winner": "A"|"B"|"tie", "score_a": float, "score_b": float}``. The JudgeLayer cache
(deduped by scenario/run/rubric/judge_model) prevents duplicate spend and is unchanged.

Import-safe at T0: the provider and ledger are injected; Lane A's
:mod:`tests.pi_benchmark.deepseek_provider` is imported only for its exception type, with
a local twin fallback until that lane lands. Assumed provider surface (per the lane
contract): ``provider.chat(*, messages, temperature, max_tokens, ledger, call_id, kind)``
returning ``(content, usage)`` like :meth:`DeepSeekProvider.chat` (a bare completion
string or an object with ``.text`` is also accepted).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from tests.pi_benchmark.judge import JudgeFn

try:  # Lane A module; fall back to a local twin until it lands.
    from tests.pi_benchmark.deepseek_provider import ProviderCallFailed
except ImportError:  # pragma: no cover - exercised only while Lane A is unmerged

    class ProviderCallFailed(RuntimeError):  # type: ignore[no-redef]
        """Fallback twin of Lane A's ProviderCallFailed (same name, same semantics)."""


VERDICT_INSTRUCTION = (
    '\n\nRespond with JSON: {"winner":"A|B|tie","score_a":1-7,"score_b":1-7}'
)

_VALID_WINNERS = ("A", "B", "TIE")


def _response_text(raw: Any) -> str:
    # DeepSeekProvider.chat returns (content, usage); fakes may return a bare string
    # or an object with .text. All three resolve to the completion text here.
    if isinstance(raw, tuple) and raw:
        raw = raw[0]
    if isinstance(raw, str):
        return raw
    text = getattr(raw, "text", None)
    if isinstance(text, str):
        return text
    return str(raw)


def parse_verdict(text: str) -> dict[str, Any]:
    """Parse a judge verdict tolerantly: the first JSON object in the text wins.

    Raises :class:`ProviderCallFailed` on a missing or malformed verdict — a judge that
    cannot answer in contract never degrades to a silent tie.
    """
    start = text.find("{")
    if start < 0:
        raise ProviderCallFailed(f"judge verdict contained no JSON object: {text[:120]!r}")
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise ProviderCallFailed(f"judge verdict JSON malformed: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderCallFailed(f"judge verdict was not a JSON object: {type(data).__name__}")
    winner = str(data.get("winner", "")).strip().upper()
    if winner not in _VALID_WINNERS:
        raise ProviderCallFailed(f"judge verdict winner invalid: {data.get('winner')!r}")
    try:
        score_a = float(data["score_a"])
        score_b = float(data["score_b"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderCallFailed(f"judge verdict scores missing/non-numeric: {exc}") from exc
    return {"winner": "tie" if winner == "TIE" else winner, "score_a": score_a, "score_b": score_b}


def make_deepseek_judge_fn(*, provider: Any, ledger: Any = None, max_tokens: int = 512) -> JudgeFn:
    """Build a JudgeLayer-compatible judge_fn backed by DeepSeek through ``provider``.

    Judge calls carry ``kind="judge"`` and share the benchmark's ledger/cap; the call id
    is deterministic per prompt (``judge-<sha256(prompt)[:16]>``) so a retried judgment
    reconciles against the same ledger entry.
    """

    def judge_fn(prompt: str, arms: dict[str, str]) -> dict[str, Any]:
        call_id = f"judge-{hashlib.sha256(prompt.encode()).hexdigest()[:16]}"
        raw = provider.chat(
            messages=[{"role": "user", "content": prompt + VERDICT_INSTRUCTION}],
            temperature=0.0,
            max_tokens=max_tokens,
            ledger=ledger,
            call_id=call_id,
            kind="judge",
        )
        return parse_verdict(_response_text(raw))

    return judge_fn
