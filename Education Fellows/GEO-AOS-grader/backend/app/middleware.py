"""HTTP middleware: request_id для логов и in-memory rate limit для /api/analyze."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Привязывает X-Request-Id ко всем логам в рамках запроса."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        with logger.contextualize(request_id=request_id):
            logger.info("→ {} {}", request.method, request.url.path)
            response = await call_next(request)
            logger.info("← {} {} [{}]", request.method, request.url.path, response.status_code)
        response.headers["X-Request-Id"] = request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """5 запросов в час на IP для POST /api/analyze.

    In-memory реализация под MVP. На масштабе заменим на Redis-token-bucket.
    """

    PROTECTED_PATH = "/api/analyze"
    PROTECTED_METHOD = "POST"
    LIMIT = 5
    WINDOW_SECONDS = 3600

    def __init__(self, app) -> None:
        super().__init__(app)
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.method != self.PROTECTED_METHOD or request.url.path != self.PROTECTED_PATH:
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.monotonic()
        cutoff = now - self.WINDOW_SECONDS

        with self._lock:
            bucket = self._buckets[ip]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.LIMIT:
                retry_after = int(bucket[0] + self.WINDOW_SECONDS - now) + 1
                logger.warning("rate_limit: ip={} reached {}/hour", ip, self.LIMIT)
                return JSONResponse(
                    status_code=429,
                    content={"detail": f"Превышен лимит: {self.LIMIT} анализов в час. Попробуй позже."},
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)

        return await call_next(request)
