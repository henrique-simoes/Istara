"""Regression test for the long-horizon token fix (task B0-3, acceptance A3).

The prior code counted one "token" per streamed SSE content chunk
(``long_horizon_runner.py`` old ``total_tokens += 1``). This test pins the corrected
behaviour: token accounting comes from provider-reported usage, never from a chunk count.
It FAILS against the old chunk-count implementation, as A3 requires.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.benchmark

# The runner module imports httpx at top level; skip cleanly if it is unavailable.
httpx = pytest.importorskip("httpx")

from tests.benchmarks.long_horizon_runner import extract_total_tokens  # noqa: E402


def test_content_chunks_are_not_counted_as_tokens():
    # Three content chunks. Old behaviour: total_tokens == 3. Correct behaviour: None
    # (the stream carried no provider usage), so this asserts the bug is gone.
    events = [
        {"type": "chunk", "content": "Hello "},
        {"type": "chunk", "content": "world"},
        {"content": "!"},
    ]
    assert extract_total_tokens(events) is None


def test_provider_reported_usage_is_read():
    events = [
        {"type": "chunk", "content": "Hi"},
        {"type": "usage", "usage": {"input_tokens": 128, "output_tokens": 64, "total_tokens": 192}},
    ]
    assert extract_total_tokens(events) == 192


def test_camelcase_usage_is_read():
    events = [{"usage": {"totalTokens": 55}}]
    assert extract_total_tokens(events) == 55


def test_empty_stream_reports_no_tokens():
    assert extract_total_tokens([]) is None
