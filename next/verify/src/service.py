"""Talking to the service through the balancer, and waiting for things to happen."""

import json
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

import live

BALANCER = "http://localhost:8000"


# --- One call ---------------------------------------------------------------------

@dataclass
class Response:
    status: int                     # 0 if nobody answered
    headers: dict = field(default_factory=dict)     # names in lowercase
    body: dict | None = None        # the JSON, if the response has any
    text: str = ""                  # the content as text, for the pages that are not JSON

    @property
    def instance(self) -> str:
        return self.headers.get("x-instance-id", "")

    @property
    def version(self) -> str | None:
        return self.headers.get("x-data-version")


def get(path: str, base: str = BALANCER, timeout: float = 3, show: bool = False) -> Response:
    """One call to the service. With `show`, it is also printed as it happens."""
    response = fetch(base + path, timeout)

    if show:
        live.request(response, path)

    return response


def fetch(url: str, timeout: float) -> Response:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            text = response.read().decode(errors="replace")

            return Response(response.status, lowercase(response.headers), parse_json(text), text)
    except urllib.error.HTTPError as error:
        return Response(error.code, lowercase(error.headers))
    except (urllib.error.URLError, OSError):
        return Response(0)


def lowercase(headers) -> dict:
    """HTTP header names are case-insensitive, so they are compared in lowercase."""
    return {name.lower(): value for name, value in headers.items()}


def parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except ValueError:
        return None


# --- Many calls -------------------------------------------------------------------

class Traffic:
    """`with Traffic() as traffic:` sends a request every `interval` seconds until the block ends.

    What came back is in `traffic.responses`.
    """

    def __init__(self, path: str = "/orders", interval: float = 0.25) -> None:
        self.path = path
        self.interval = interval
        self.responses: list[Response] = []
        self._running = threading.Event()
        self._thread = threading.Thread(target=self._send, daemon=True)

    def __enter__(self):
        self._running.set()
        self._thread.start()

        return self

    def __exit__(self, *error) -> None:
        self._running.clear()
        self._thread.join()

    def _send(self) -> None:
        while self._running.is_set():
            self.responses.append(get(self.path, show=True))
            time.sleep(self.interval)


def success_rate(responses: list[Response]) -> float:
    return sum(r.status == 200 for r in responses) / len(responses) if responses else 0


# --- Waiting ----------------------------------------------------------------------

def wait_until(condition, timeout: float, interval: float = 1) -> float | None:
    """Seconds until the condition holds, or None if it does not within the timeout."""
    start = time.monotonic()

    while time.monotonic() - start < timeout:
        if condition():
            return time.monotonic() - start

        time.sleep(interval)

    return None
