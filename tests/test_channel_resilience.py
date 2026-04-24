"""Tests for channel resilience utilities — retry, circuit breaker, idempotency."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.core.channel_resilience import (
    CircuitBreaker,
    CircuitBreakerOpen,
    retry_with_backoff,
)


@pytest.mark.asyncio
async def test_retry_with_backoff_succeeds_on_first_try():
    """Retry should return immediately on success."""
    mock_fn = AsyncMock(return_value="ok")
    result = await retry_with_backoff(mock_fn, max_retries=2, base_delay=0.01)
    assert result == "ok"
    assert mock_fn.call_count == 1


@pytest.mark.asyncio
async def test_retry_with_backoff_retries_then_succeeds():
    """Retry should recover after transient failures."""
    mock_fn = AsyncMock(side_effect=[RuntimeError("fail 1"), RuntimeError("fail 2"), "ok"])
    result = await retry_with_backoff(mock_fn, max_retries=3, base_delay=0.01)
    assert result == "ok"
    assert mock_fn.call_count == 3


@pytest.mark.asyncio
async def test_retry_with_backoff_raises_after_exhaustion():
    """Retry should raise the last exception when all retries are exhausted."""
    mock_fn = AsyncMock(side_effect=RuntimeError("persistent"))
    with pytest.raises(RuntimeError, match="persistent"):
        await retry_with_backoff(mock_fn, max_retries=1, base_delay=0.01)
    assert mock_fn.call_count == 2  # initial + 1 retry


@pytest.mark.asyncio
async def test_circuit_breaker_allows_calls_when_closed():
    """Breaker should pass calls through when closed."""
    breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    mock_fn = AsyncMock(return_value="ok")
    result = await breaker.call(mock_fn)
    assert result == "ok"


@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Breaker should open after threshold failures."""
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=60.0)
    mock_fn = AsyncMock(side_effect=RuntimeError("boom"))

    # First failure
    with pytest.raises(RuntimeError):
        await breaker.call(mock_fn)
    # Second failure — should open the breaker
    with pytest.raises(RuntimeError):
        await breaker.call(mock_fn)

    # Third call should fail fast with CircuitBreakerOpen
    with pytest.raises(CircuitBreakerOpen):
        await breaker.call(mock_fn)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout():
    """Breaker should move to half-open after recovery timeout."""
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
    mock_fn = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        await breaker.call(mock_fn)

    # Wait for recovery timeout
    await asyncio.sleep(0.1)

    # Should be half-open now — allow probe
    with pytest.raises(RuntimeError):
        await breaker.call(mock_fn)

    # Breaker should be open again after probe failure
    with pytest.raises(CircuitBreakerOpen):
        await breaker.call(AsyncMock())


@pytest.mark.asyncio
async def test_circuit_breaker_closes_on_success():
    """Breaker should close again after a successful probe."""
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.05)
    failing_fn = AsyncMock(side_effect=RuntimeError("boom"))

    with pytest.raises(RuntimeError):
        await breaker.call(failing_fn)

    await asyncio.sleep(0.1)

    # Successful probe should close the breaker
    ok_fn = AsyncMock(return_value="ok")
    result = await breaker.call(ok_fn)
    assert result == "ok"
    assert breaker.state == "closed"


@pytest.mark.asyncio
async def test_whatsapp_webhook_idempotency():
    """WhatsApp adapter should deduplicate webhook messages by external_message_id."""
    from app.channels.whatsapp import WhatsAppAdapter

    adapter = WhatsAppAdapter(
        "test-instance", {"phone_number_id": "123", "access_token": "abc"}
    )
    adapter._running = True
    callback = AsyncMock(return_value=None)
    adapter.on_message(callback)

    msg1 = {
        "id": "msg-id-001",
        "type": "text",
        "from": "1234567890",
        "text": {"body": "Hello"},
    }
    msg2 = {
        "id": "msg-id-001",  # same id
        "type": "text",
        "from": "1234567890",
        "text": {"body": "Hello duplicate"},
    }

    await adapter._process_webhook_message(msg1, {"1234567890": "Ada"})
    await adapter._process_webhook_message(msg2, {"1234567890": "Ada"})

    assert callback.call_count == 1
    assert "msg-id-001" in adapter._seen_message_ids


@pytest.mark.asyncio
async def test_whatsapp_webhook_missing_id_is_not_globally_deduplicated():
    """WhatsApp messages without IDs should still be processed independently."""
    from app.channels.whatsapp import WhatsAppAdapter

    adapter = WhatsAppAdapter(
        "test-instance", {"phone_number_id": "123", "access_token": "abc"}
    )
    adapter._running = True
    callback = AsyncMock(return_value=None)
    adapter.on_message(callback)

    await adapter._process_webhook_message(
        {
            "type": "text",
            "from": "1234567890",
            "text": {"body": "First"},
        },
        {"1234567890": "Ada"},
    )
    await adapter._process_webhook_message(
        {
            "type": "text",
            "from": "1234567890",
            "text": {"body": "Second"},
        },
        {"1234567890": "Ada"},
    )

    assert callback.call_count == 2
    assert "" not in adapter._seen_message_ids
