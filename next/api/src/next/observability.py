"""Observability: JSON logs, instance header and one log line per request."""

import json
import logging
import time
from datetime import datetime, timezone

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("next")


class JsonFormatter(logging.Formatter):
    """Formats every log record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        line = {
            "ts": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            line["exception"] = self.formatException(record.exc_info)
        return json.dumps(line)


def configure_logging(level: str) -> None:
    """Send all logs (ours and uvicorn's) to stdout as JSON."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers.clear()
    # Requests are logged by RequestLogMiddleware, so uvicorn's access log is off.
    logging.getLogger("uvicorn.access").disabled = True


class InstanceHeaderMiddleware(BaseHTTPMiddleware):
    """Adds `X-Instance-Id` to every response, including errors."""

    def __init__(self, app, instance_id: str) -> None:
        super().__init__(app)
        self._instance_id = instance_id

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        try:
            response = await call_next(request)
        except Exception:
            logger.exception("unhandled error")
            response = JSONResponse({"error": "Internal server error"}, status_code=500)
        response.headers["X-Instance-Id"] = self._instance_id
        return response


class RequestLogMiddleware(BaseHTTPMiddleware):
    """Writes one log line per request."""

    def __init__(self, app, instance_id: str) -> None:
        super().__init__(app)
        self._instance_id = instance_id

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        fields = {
            "instance": self._instance_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((time.perf_counter() - start) * 1000, 2),
            "data_version": getattr(request.state, "data_version", None),
        }
        logger.info("request", extra={"fields": fields})
        return response
