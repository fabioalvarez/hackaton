"""Middlewares: instance header and one log line per request."""

import logging
import time

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from next.observability import logger


class InstanceMiddleware(BaseHTTPMiddleware):
    """Base for the middlewares that need to know which instance they run on."""

    def __init__(self, app, instance_id: str) -> None:
        super().__init__(app)
        self.instance_id = instance_id


class InstanceHeaderMiddleware(InstanceMiddleware):
    """Adds `X-Instance-Id` to every response, including errors."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "unhandled error",
                extra={
                    "fields": {
                        "instance": self.instance_id,
                        "method": request.method,
                        "path": request.url.path,
                    }
                },
            )
            response = JSONResponse({"error": "Internal server error"}, status_code=500)

        response.headers["X-Instance-Id"] = self.instance_id

        return response


class RequestLogMiddleware(InstanceMiddleware):
    """Writes one log line per request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)

        # Health checks run every few seconds: only visible at DEBUG, unless they fail.
        is_health_ok = request.url.path == "/health" and response.status_code < 400
        level = logging.DEBUG if is_health_ok else logging.INFO

        logger.log(
            level,
            "request",
            extra={
                "fields": {
                    "instance": self.instance_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - start) * 1000, 2),
                    "data_version": getattr(request.state, "data_version", None),
                }
            },
        )

        return response
