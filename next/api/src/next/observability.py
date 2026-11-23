"""Observability: JSON logs."""

import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger("next")


class JsonFormatter(logging.Formatter):
    """Formats every log record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.fromtimestamp(record.created, timezone.utc).isoformat()
        line = {
            "ts": ts,
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
