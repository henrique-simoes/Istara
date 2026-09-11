"""Regression tests for the Slack adapter's slack_sdk-compatible client seam.

``SlackAdapter.send`` and ``health_check`` call whichever client
``_create_client()`` returns by duck typing: slack_sdk's ``AsyncWebClient``
when ``slack-bolt[async]`` (and aiohttp) is importable, or the httpx-backed
``_HttpxSlackClient`` fallback otherwise. Both classes must therefore expose
the same API names.

F-CI-R1-1 regression: an N802 lint fix renamed ``chat_postMessage`` to
``chat_post_message`` on the raw client, which silently broke every outbound
send on the AsyncWebClient path (AttributeError, retried three times, never
reached the network). These tests pin the adapter to the slack_sdk names.
"""

from __future__ import annotations

import pytest
from app.channels.base import OutgoingMessage
from app.channels.slack import SlackAdapter, _HttpxSlackClient

# Method names the adapter calls by duck typing. ``chat_postMessage`` keeps its
# camelCase form on purpose: it mirrors slack_sdk's AsyncWebClient API.
_ADAPTER_CLIENT_API = ("auth_test", "chat_postMessage", "files_upload_v2")

try:  # Importing the async client also needs aiohttp (slack-bolt[async] extra).
    from slack_sdk.web.async_client import AsyncWebClient

    _SLACK_SDK_ASYNC_IMPORTABLE = True
except ImportError:  # pragma: no cover - dev venvs may omit the extra
    AsyncWebClient = None  # type: ignore[assignment,misc]
    _SLACK_SDK_ASYNC_IMPORTABLE = False


class _FakeSlackSdkClient:
    """Fake exposing only the slack_sdk ``AsyncWebClient`` API names."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def chat_postMessage(self, **kwargs) -> dict:  # noqa: N802 - mirrors slack_sdk API
        self.calls.append(("chat_postMessage", kwargs))
        return {"ok": True, "ts": "1000.000"}

    async def files_upload_v2(self, **kwargs) -> dict:
        self.calls.append(("files_upload_v2", kwargs))
        return {"ok": True}

    async def auth_test(self) -> dict:
        self.calls.append(("auth_test", {}))
        return {"ok": True}


def _running_adapter(client) -> SlackAdapter:
    adapter = SlackAdapter(
        instance_id="probe",
        config={"bot_token": "xoxb-test", "signing_secret": "signing-secret"},
    )
    adapter._client = client
    adapter._running = True
    return adapter


def test_httpx_fallback_client_exposes_slack_sdk_api_names():
    """The httpx fallback must keep the AsyncWebClient method names send() calls."""
    for name in _ADAPTER_CLIENT_API:
        assert callable(getattr(_HttpxSlackClient, name, None)), name


def test_create_client_returns_ducktyped_client():
    """Whichever client _create_client() returns must expose the duck-typed API."""
    adapter = SlackAdapter(
        instance_id="probe",
        config={"bot_token": "xoxb-test", "signing_secret": "signing-secret"},
    )
    client = adapter._create_client()
    for name in _ADAPTER_CLIENT_API:
        assert callable(getattr(client, name, None)), name


@pytest.mark.asyncio
async def test_send_calls_only_slack_sdk_method_names(monkeypatch):
    """send() must call only names that exist on slack_sdk AsyncWebClient.

    The fake exposes exactly the AsyncWebClient names, so a caller rename
    (e.g. to ``chat_post_message``) fails with AttributeError here instead of
    silently breaking the real slack_sdk client path.
    """
    # This test pins the method name, not the backoff: retry sleeps would only
    # slow the failure path (covered in test_channel_resilience.py).
    monkeypatch.setattr("app.core.channel_resilience.retry_with_backoff", lambda fn, **_: fn())
    fake = _FakeSlackSdkClient()
    adapter = _running_adapter(fake)

    await adapter.send(
        OutgoingMessage(
            channel="slack",
            channel_id="C1",
            text="hi",
            metadata={"thread_ts": "123.456", "blocks": [{"type": "section"}]},
        )
    )

    assert [name for name, _ in fake.calls] == ["chat_postMessage"]
    assert fake.calls[0][1] == {
        "channel": "C1",
        "text": "hi",
        "thread_ts": "123.456",
        "blocks": [{"type": "section"}],
    }


@pytest.mark.asyncio
async def test_send_uploads_attachments_with_slack_sdk_method_name(monkeypatch, tmp_path):
    monkeypatch.setattr("app.core.channel_resilience.retry_with_backoff", lambda fn, **_: fn())
    fake = _FakeSlackSdkClient()
    adapter = _running_adapter(fake)
    attachment = tmp_path / "evidence.txt"
    attachment.write_text("evidence")

    await adapter.send(
        OutgoingMessage(
            channel="slack",
            channel_id="C1",
            text="report",
            attachments=[str(attachment)],
        )
    )

    assert [name for name, _ in fake.calls] == ["chat_postMessage", "files_upload_v2"]
    assert fake.calls[1][1] == {
        "channel": "C1",
        "file": str(attachment),
        "thread_ts": None,
    }


@pytest.mark.asyncio
async def test_health_check_uses_slack_sdk_method_name():
    fake = _FakeSlackSdkClient()
    adapter = _running_adapter(fake)

    result = await adapter.health_check()

    assert [name for name, _ in fake.calls] == ["auth_test"]
    assert result == {
        "status": "healthy",
        "platform": "slack",
        "team": "",
        "user": "",
        "bot_id": "",
    }


@pytest.mark.skipif(
    not _SLACK_SDK_ASYNC_IMPORTABLE,
    reason="slack_sdk async client needs aiohttp (slack-bolt[async] extra)",
)
def test_api_name_parity_with_slack_sdk_async_web_client():
    """The duck-typed names used by the adapter exist on both client classes."""
    for name in _ADAPTER_CLIENT_API:
        assert callable(getattr(AsyncWebClient, name, None)), name
        assert callable(getattr(_HttpxSlackClient, name, None)), name
