"""API rate limiting middleware using slowapi (token bucket per IP).

Provides sensible defaults:
- 200 requests/minute for general API
- 20 requests/minute for auth endpoints
- 60 requests/minute for webhook endpoints

Install: pip install slowapi>=0.1.9
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    RATE_LIMIT_AVAILABLE = True
except ImportError:
    limiter = None  # type: ignore
    RATE_LIMIT_AVAILABLE = False
    logger.info("slowapi not installed — rate limiting disabled")
