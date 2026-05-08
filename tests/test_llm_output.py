"""Tests for provider-neutral LLM output normalization."""

import json

from app.core.llm_output import (
    ThinkingContentFilter,
    visible_assistant_content,
    visible_assistant_message,
)
from app.core.llm_thinking import (
    apply_thinking_control,
    normalize_thinking_mode,
    thinking_marker_registry,
)


def test_visible_content_ignores_structured_reasoning_fields():
    message = {
        "role": "assistant",
        "content": "",
        "reasoning_content": "private chain of thought",
    }

    assert visible_assistant_content(message) == ""


def test_visible_message_removes_structured_reasoning_fields():
    message = {
        "role": "assistant",
        "content": "<think>private</think>\n\nFinal answer.",
        "reasoning_content": "private chain of thought",
        "thinking": "also private",
    }

    assert visible_assistant_message(message) == {
        "role": "assistant",
        "content": "Final answer.",
    }


def test_visible_content_strips_inline_qwen_thinking_block():
    message = {
        "role": "assistant",
        "content": "<think>\nprivate reasoning\n</think>\n\nFinal answer.",
    }

    assert visible_assistant_content(message) == "Final answer."


def test_visible_content_strips_gemma_thought_channel():
    message = {
        "role": "assistant",
        "content": "<|channel>thought\nprivate reasoning\n<channel|>Final answer.<turn|>",
    }

    assert visible_assistant_content(message) == "Final answer."


def test_visible_content_ignores_gemini_thought_parts():
    message = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "hidden", "thought": True},
            {"type": "text", "text": "Visible answer."},
            {"type": "text", "text": " Signed visible.", "thoughtSignature": "opaque"},
        ],
    }

    assert visible_assistant_content(message) == "Visible answer. Signed visible."


def test_visible_content_preserves_structured_json_payloads():
    message = {
        "role": "assistant",
        "content": {
            "summary": "NPS increased among enterprise users.",
            "nuggets": [{"label": "enterprise", "score": 42}],
        },
    }

    content = visible_assistant_content(message)

    assert json.loads(content) == message["content"]


def test_visible_content_uses_parsed_payload_when_content_is_empty():
    message = {
        "role": "assistant",
        "content": "",
        "parsed": {
            "summary": "Structured output came from the provider parser.",
            "facts": [{"text": "Parser returned an object."}],
        },
    }

    assert json.loads(visible_assistant_content(message)) == message["parsed"]


def test_visible_content_preserves_structured_json_blocks():
    message = {
        "role": "assistant",
        "content": [
            {"type": "text", "text": "{"},
            {"summary": "User flow friction was concentrated at onboarding."},
            {"type": "text", "text": "}"},
        ],
    }

    assert '"summary": "User flow friction was concentrated at onboarding."' in visible_assistant_content(message)


def test_streaming_filter_suppresses_split_thinking_block():
    stream_filter = ThinkingContentFilter()

    chunks = [
        stream_filter.push("<thi"),
        stream_filter.push("nk>\nprivate"),
        stream_filter.push(" reasoning\n</thi"),
        stream_filter.push("nk>\n\nFinal"),
        stream_filter.flush(),
    ]

    assert "".join(chunks) == "Final"


def test_streaming_filter_suppresses_split_gemma_thought_channel():
    stream_filter = ThinkingContentFilter()

    chunks = [
        stream_filter.push("<|chan"),
        stream_filter.push("nel>thought\nprivate"),
        stream_filter.push(" reasoning\n<chan"),
        stream_filter.push("nel|>Final<tur"),
        stream_filter.push("n|>"),
        stream_filter.flush(),
    ]

    assert "".join(chunks) == "Final"


def test_thinking_control_injects_off_directive_once():
    messages = [{"role": "system", "content": "Base system."}, {"role": "user", "content": "Hi"}]

    controlled = apply_thinking_control(messages, "off")
    controlled_again = apply_thinking_control(controlled, "off")

    assert "Istara thinking mode is OFF" in controlled[0]["content"]
    assert controlled_again[0]["content"].count("Istara thinking mode is OFF") == 1
    assert messages[0]["content"] == "Base system."


def test_thinking_mode_normalization_and_marker_registry():
    assert normalize_thinking_mode("server-default") == "server_default"
    assert normalize_thinking_mode("chaos") == "server_default"
    registry = thinking_marker_registry()
    assert ("<think>", "</think>") in registry["qwen"]["inline_blocks"]
    assert ("<|channel>thought", "<channel|>") in registry["gemma"]["inline_blocks"]
    assert "reasoning_content" in registry["openai"]["structured_keys"]
    assert "redacted_thinking" in registry["anthropic"]["structured_types"]
