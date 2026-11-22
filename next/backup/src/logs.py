"""One JSON line per log, with only its level and what is happening."""

import json

LEVELS = {"debug": 10, "info": 20, "error": 40}

# Logs below this level are not printed. Set once at startup with `configure`.
min_level = LEVELS["info"]


def configure(level: str) -> None:
    global min_level
    min_level = LEVELS[level.lower()]


def log(detail: str, level: str = "info") -> None:
    if LEVELS[level] >= min_level:
        print(json.dumps({"level": level, "detail": detail}), flush=True)
