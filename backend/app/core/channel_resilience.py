"""Resilience utilities for channel adapters — retry, circuit breaker, idempotency.

These patterns protect Istara from cascading failures when upstream
messaging APIs (Telegram, WhatsApp, Slack) are temporarily unavailable.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Exponential backoff retry
# ---------------------------------------------------------------------------


async def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> T:
    """Retry an async callable with exponential backoff and jitter.

    Args:
        fn: The async callable to retry.
        max_retries: Maximum number of retry attempts after the first failure.
        base_delay: Initial delay in seconds.
        max_delay: Cap on delay between retries.
        exceptions: Tuple of exception types that should trigger a retry.

    Returns:
        The result of ``fn()`` on success.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except exceptions as exc:
            last_exc = exc
            if attempt >= max_retries:
                break
            delay = min(base_delay * (2**attempt), max_delay)
            # Simple full-jitter to avoid thundering herd
            jittered = delay * (0.5 + 0.5 * (time.time() % 1))
            logger.warning(
                "Retryable error on attempt %d/%d, waiting %.2fs: %s",
                attempt + 1,
                max_retries + 1,
                jittered,
                exc,
            )
            await asyncio.sleep(jittered)

    raise last_exc  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


@dataclass
class CircuitBreaker:
    """Simple circuit breaker for outbound HTTP calls.

    Opens after *failure_threshold* consecutive failures within
    *recovery_timeout* seconds.  While open, calls fail fast with
    :class:`CircuitBreakerOpen`.  After the timeout the breaker moves
    to half-open and allows one probe call.
    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 1

    _failures: int = field(default=0, repr=False)
    _last_failure_at: float = field(default=0.0, repr=False)
    _state: str = field(default="closed", repr=False)  # closed|open|half_open
    _half_open_calls: int = field(default=0, repr=False)

    @property
    def state(self) -> str:
        if self._state == "open":
            if time.time() - self._last_failure_at >= self.recovery_timeout:
                self._state = "half_open"
                self._half_open_calls = 0
        return self._state

    def _record_success(self) -> None:
        self._failures = 0
        self._state = "closed"
        self._half_open_calls = 0

    def _record_failure(self) -> None:
        self._failures += 1
        self._last_failure_at = time.time()
        if self._failures >= self.failure_threshold:
            self._state = "open"

    async def call(self, fn: Callable[[], T]) -> T:
        """Execute *fn* through the breaker."""
        st = self.state
        if st == "open":
            raise CircuitBreakerOpen(
                f"Circuit breaker open (last failure {self._last_failure_at:.0f})"
            )
        if st == "half_open":
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpen("Circuit breaker half-open, probe in progress")
            self._half_open_calls += 1

        try:
            result = await fn()
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise


class CircuitBreakerOpen(Exception):
    """Raised when the circuit breaker is open."""

    pass


# ---------------------------------------------------------------------------
# Decorator helpers
# ---------------------------------------------------------------------------


def resilient_send(
    max_retries: int = 3,
    base_delay: float = 1.0,
    breaker: CircuitBreaker | None = None,
):
    """Decorator that wraps an async ``send`` method with retry + circuit breaker.

    Usage::

        class MyAdapter(ChannelAdapter):
            @resilient_send()
            async def send(self, message: OutgoingMessage) -> None:
                ...
    """

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            async def _call() -> Any:
                return await fn(*args, **kwargs)

            if breaker is not None:
                return await breaker.call(
                    lambda: retry_with_backoff(_call, max_retries=max_retries, base_delay=base_delay)
                )
            return await retry_with_backoff(_call, max_retries=max_retries, base_delay=base_delay)

        return wrapper

    return decorator
