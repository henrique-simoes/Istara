"""Vision-capable compute routing and donated-model capability tests."""

import httpx
import pytest

from app.core.compute_registry import ComputeNode, ComputeRegistry
from app.core.model_capabilities import _capability_from_lmstudio_model


class _SuccessfulChatClient:
    def __init__(self, content: str = "vision answered"):
        self.calls = 0
        self.paths: list[str] = []
        self.payloads: list[dict] = []
        self.content = content

    async def post(self, path: str, json: dict):
        self.calls += 1
        self.paths.append(path)
        self.payloads.append(json)
        return httpx.Response(
            200,
            request=httpx.Request("POST", f"http://test/{path}"),
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": self.content,
                        }
                    }
                ]
            },
        )


class _VisionLoadChatClient:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def post(self, path: str, json: dict, timeout=None):
        self.calls.append((path, json))
        if path == "api/v1/models/load":
            return httpx.Response(
                200,
                request=httpx.Request("POST", "http://test/api/v1/models/load"),
                json={"status": "loaded", "type": "llm", "instance_id": json["model"]},
            )
        if path == "v1/chat/completions":
            return httpx.Response(
                200,
                request=httpx.Request("POST", "http://test/v1/chat/completions"),
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "vision answered",
                            }
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected path {path}")


def _image_content() -> list[dict]:
    return [
        {"type": "text", "text": "Inspect this UI"},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}},
    ]


def test_lmstudio_metadata_marks_qwen36_as_loaded_vision_model():
    cap = _capability_from_lmstudio_model(
        {
            "key": "qwen3.6-35b-a3b",
            "type": "vlm",
            "capabilities": {"vision": True, "trained_for_tool_use": True},
            "loaded_instances": [
                {"id": "qwen3.6-35b-a3b", "config": {"context_length": 100000}}
            ],
            "quantization": {"name": "Q5_K_XL"},
        }
    )

    assert cap is not None
    assert cap.name == "qwen3.6-35b-a3b"
    assert cap.supports_vision is True
    assert cap.supports_tools is True
    assert cap.is_loaded is True
    assert cap.context_length == 100000
    assert cap.quantization == "Q5_K_XL"


def test_select_candidates_hard_filters_vision_requirement():
    registry = ComputeRegistry()
    text_only = ComputeNode(
        node_id="text",
        name="Text",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["text-model"],
        model_capabilities={"text-model": {"supports_vision": False}},
    )
    vision = ComputeNode(
        node_id="vision",
        name="Vision",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["vision-model"],
        model_capabilities={"vision-model": {"supports_vision": True}},
    )
    registry.register_node(text_only)
    registry.register_node(vision)

    candidates = registry._select_candidates(require_vision=True)

    assert [node.node_id for node in candidates] == ["vision"]


def test_sanitize_messages_preserves_openai_multimodal_content():
    image_content = _image_content()

    sanitized = ComputeRegistry._sanitize_messages([{"role": "user", "content": image_content}])

    assert sanitized == [{"role": "user", "content": image_content}]
    assert ComputeRegistry._messages_require_vision(sanitized) is True


@pytest.mark.asyncio
async def test_list_models_includes_capability_metadata_for_relay_nodes():
    registry = ComputeRegistry()
    node = ComputeNode(
        node_id="relay",
        name="Relay",
        host="http://192.0.2.142:1234",
        source="relay",
        provider_type="lmstudio",
        is_healthy=True,
        last_heartbeat=9999999999,
        loaded_models=["qwen3.6-35b-a3b"],
        allowed_project_ids=["project-a"],
        model_capabilities={
            "qwen3.6-35b-a3b": {
                "supports_tools": True,
                "supports_vision": True,
                "context_length": 262144,
                "parameter_count": "35B",
                "quantization": "Q5_K_XL",
                "is_loaded": True,
            }
        },
    )
    registry.register_node(node)

    models = await registry.list_models(project_id="project-a")

    assert models == [
        {
            "name": "qwen3.6-35b-a3b",
            "id": "qwen3.6-35b-a3b",
            "_server": "Relay",
            "_server_id": "relay",
            "supports_tools": True,
            "supports_vision": True,
            "supports_audio": False,
            "supports_json": False,
            "context_length": 262144,
            "trained_context_length": None,
            "loaded_context_length": None,
            "parameter_count": "35B",
            "quantization": "Q5_K_XL",
            "is_loaded": True,
            "endpoint_family": None,
            "capabilities": {"tools": True, "vision": True, "audio": False, "json": False},
        }
    ]


@pytest.mark.asyncio
async def test_chat_routes_image_payload_to_vision_node(monkeypatch):
    registry = ComputeRegistry()
    text_client = _SuccessfulChatClient("text should not answer")
    vision_client = _SuccessfulChatClient("vision answered")
    text_node = ComputeNode(
        node_id="text",
        name="Text",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=0,
        loaded_models=["text-model"],
        model_capabilities={"text-model": {"supports_vision": False, "is_loaded": True}},
    )
    vision_node = ComputeNode(
        node_id="vision",
        name="Vision",
        host="http://localhost:1235",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        priority=10,
        loaded_models=["vision-model"],
        model_capabilities={"vision-model": {"supports_vision": True, "is_loaded": True}},
    )

    async def text_get_client():
        return text_client

    async def vision_get_client():
        return vision_client

    monkeypatch.setattr(text_node, "_get_client", text_get_client)
    monkeypatch.setattr(vision_node, "_get_client", vision_get_client)
    registry.register_node(text_node)
    registry.register_node(vision_node)

    image_content = _image_content()
    response = await registry.chat([{"role": "user", "content": image_content}])

    assert response["message"]["content"] == "vision answered"
    assert text_client.calls == 0
    assert vision_client.calls == 1
    assert vision_client.payloads[0]["messages"][0]["content"] == image_content


@pytest.mark.asyncio
async def test_chat_loads_available_lmstudio_vision_model_for_image_task(monkeypatch):
    registry = ComputeRegistry()
    client = _VisionLoadChatClient()
    node = ComputeNode(
        node_id="vision",
        name="Vision",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["text-model", "vision-model"],
        model_capabilities={
            "text-model": {"supports_vision": False, "is_loaded": True},
            "vision-model": {"supports_vision": True, "is_loaded": False},
        },
    )

    async def get_client():
        return client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    image_content = _image_content()
    response = await registry.chat([{"role": "user", "content": image_content}])

    assert response["message"]["content"] == "vision answered"
    assert [path for path, _ in client.calls] == ["api/v1/models/load", "v1/chat/completions"]
    assert client.calls[0][1]["model"] == "vision-model"
    assert client.calls[1][1]["model"] == "vision-model"
    assert client.calls[1][1]["messages"][0]["content"] == image_content
    assert node.model_capabilities["vision-model"]["is_loaded"] is True


@pytest.mark.asyncio
async def test_chat_rejects_image_task_without_vision_capability(monkeypatch):
    registry = ComputeRegistry()
    text_client = _SuccessfulChatClient()
    node = ComputeNode(
        node_id="text",
        name="Text",
        host="http://localhost:1234",
        source="local",
        provider_type="lmstudio",
        is_healthy=True,
        loaded_models=["text-model"],
        model_capabilities={"text-model": {"supports_vision": False, "is_loaded": True}},
    )

    async def get_client():
        return text_client

    monkeypatch.setattr(node, "_get_client", get_client)
    registry.register_node(node)

    with pytest.raises(RuntimeError, match="No vision-capable compute nodes"):
        await registry.chat([{"role": "user", "content": _image_content()}])

    assert text_client.calls == 0
