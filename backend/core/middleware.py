"""Middleware đo thời gian xử lý mỗi request."""
import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.request")


class ProcessTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-ms"] = f"{elapsed_ms:.2f}"
        logger.info("%s %s -> %s (%.2f ms)", request.method, request.url.path,
                    response.status_code, elapsed_ms)
        return response
