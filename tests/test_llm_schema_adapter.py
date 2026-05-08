from app.core.compute_node_transport import ComputeNodeTransportMixin
from app.core.llm_schema_adapter import (
    ANTHROPIC_STRUCTURED_TOOL_NAME,
    normalize_anthropic_structured_tool_block,
    openai_json_schema_response_format,
    parse_json_object,
    provider_response_format_fields,
    strip_thinking_markers,
)


def test_provider_response_format_fields_preserve_openai_compatible_shape():
    response_format = openai_json_schema_response_format(
        name="sample",
        schema={"type": "object", "properties": {"summary": {"type": "string"}}},
    )

    fields = provider_response_format_fields("lmstudio", response_format)

    assert fields == {"response_format": response_format}


def test_provider_response_format_fields_translate_ollama_to_raw_schema():
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
    response_format = openai_json_schema_response_format(name="sample", schema=schema)

    fields = provider_response_format_fields("ollama", response_format)

    assert fields == {"format": schema}


def test_anthropic_payload_forces_structured_output_tool():
    schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
    response_format = openai_json_schema_response_format(name="sample", schema=schema)

    payload = ComputeNodeTransportMixin._anthropic_payload(
        [{"role": "user", "content": "Return JSON"}],
        "claude-test",
        0.2,
        100,
        response_format=response_format,
    )

    assert payload["tool_choice"] == {
        "type": "tool",
        "name": ANTHROPIC_STRUCTURED_TOOL_NAME,
    }
    assert payload["tools"][0]["input_schema"] == schema


def test_anthropic_structured_tool_block_normalizes_to_json_content():
    content = normalize_anthropic_structured_tool_block(
        {
            "type": "tool_use",
            "name": ANTHROPIC_STRUCTURED_TOOL_NAME,
            "input": {"summary": "ok"},
        }
    )

    assert content == '{"summary": "ok"}'


def test_parse_json_object_skips_visible_thinking_and_prose_braces():
    content = (
        "<think>{not json}</think>\n"
        "I considered {also not json}.\n"
        '```json\n{"summary": "ok"}\n```'
    )

    assert parse_json_object(content) == {"summary": "ok"}


def test_strip_thinking_markers_supports_common_local_model_tags():
    content = "<think>private</think><thought>hidden</thought><thinking>also hidden</thinking>{\"summary\":\"ok\"}"

    assert strip_thinking_markers(content) == '{"summary":"ok"}'
