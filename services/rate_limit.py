"""Operational HTTP rate limiting (P8-003).

Disabled by default in ``SAS_EXECUTION_MODE=certification`` so the harness is
not throttled. Production may enable a simple per-client token bucket.
"""

from __future__ import annotations

import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config import get_settings


class _TokenBucket:
    __slots__ = ("tokens", "updated_at")

    def __init__(self, *, capacity: float) -> None:
        self.tokens = capacity
        self.updated_at = time.monotonic()


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._lock = threading.Lock()
        self._buckets: dict[str, _TokenBucket] = {}

    def _enabled(self) -> bool:
        settings = get_settings()
        if settings.sas_execution_mode == "certification":
            return False
        return bool(settings.sas_rate_limit_enabled)

    def _client_key(self, request: Request) -> str:
        # Prefer mTLS fingerprint when present; else peer host.
        fp = request.headers.get("x-ssl-client-sha1") or ""
        if fp.strip():
            return f"cert:{fp.strip().upper()}"
        client = request.client
        if client is not None:
            return f"ip:{client.host}"
        return "ip:unknown"

    def _allow(self, key: str) -> bool:
        settings = get_settings()
        rate = float(settings.sas_rate_limit_per_second)
        burst = float(settings.sas_rate_limit_burst)
        if rate <= 0 or burst <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _TokenBucket(capacity=burst)
                self._buckets[key] = bucket
            elapsed = max(0.0, now - bucket.updated_at)
            bucket.tokens = min(burst, bucket.tokens + elapsed * rate)
            bucket.updated_at = now
            if bucket.tokens < 1.0:
                return False
            bucket.tokens -= 1.0
            return True

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self._enabled():
            return await call_next(request)
        # Admin metrics/health-style GET should not consume much budget, but we
        # still count them; certification mode already disables this middleware.
        if not self._allow(self._client_key(request)):
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        return await call_next(request)
