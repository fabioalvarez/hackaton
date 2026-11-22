"""One JSON line per event, so the logs can be filtered with jq."""

import json
from datetime import datetime, timezone


def log(event: str, version: str = "", detail: str = "") -> None:
    """Prints the event as a JSON line."""

    line = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "event": event,
        "version": version,
        "detail": detail,
    }
    
    print(json.dumps(line), flush=True)
