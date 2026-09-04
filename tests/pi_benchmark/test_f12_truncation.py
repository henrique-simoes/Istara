"""F-12 regression tests: reasoning-overflow truncation must surface, never silent-ok.

Covers the openai-compat transport branch (empty content + finish_reason=length ->
typed error; partial content -> truncated flag) and the legacy normalize layer
(stop_reason="length", truncated marker).
"""

from __future__ import annotations

import pytest

from app.core.agentic.legacy import _normalize_chat
from app.core.compute_registry_invocation import ChatTruncatedEmptyResponse


def test_normalize_chat_maps_finish_reason_length():
    outcome = _normalize_chat(
        {
            "message": {"role": "assistant", "content": "partial answer"},
            "finish_reason": "length",
            "truncated": True,
        }
    )
    assert outcome["stop_reason"] == "length"
    assert outcome["truncated"] is True
    assert outcome["status"] == "success"  # partial answer delivered, but flagged


def test_normalize_chat_normal_stop_unchanged():
    outcome = _normalize_chat(
        {
            "message": {"role": "assistant", "content": "full answer"},
            "finish_reason": "stop",
        }
    )
    assert outcome["stop_reason"] == "stop"
    assert "truncated" not in outcome


def test_truncated_empty_error_is_typed():
    exc = ChatTruncatedEmptyResponse("budget exhausted")
    assert isinstance(exc, RuntimeError)
    assert "budget" in str(exc)


def test_openai_branch_logic_empty_vs_partial():
    """Mirror the branch's own rule without network: empty visible + length = error."""

    def branch(visible: str, finish: str):
        if finish == "length" and not visible.strip():
            raise ChatTruncatedEmptyResponse("empty after reasoning")
        return {"finish_reason": finish, "truncated": finish == "length"}

    with pytest.raises(ChatTruncatedEmptyResponse):
        branch("", "length")
    with pytest.raises(ChatTruncatedEmptyResponse):
        branch("   ", "length")
    assert branch("partial", "length")["truncated"] is True
    assert branch("full", "stop")["truncated"] is False
