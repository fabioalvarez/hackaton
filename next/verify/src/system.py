"""Everything the checks need from the running environment: docker, the balancer, files."""

import json
import os
import re
import subprocess
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import live

ROOT = Path(__file__).resolve().parents[2]      # the `next/` folder
BALANCER = "http://localhost:8000"
VOLUME = "next_orders-data"


# --- Commands ----------------------------------------------------------------

def environment() -> dict:
    """The environment of the commands. TAG is the version that runs, as `make` sets it:
    without it, docker compose would think the image changed and recreate every container."""
    return {**os.environ, "TAG": current_tag()}


def run(*command: str, check: bool = True) -> str:
    """Runs a command from `next/` and returns its output."""
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, env=environment())

    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)}\n{result.stderr.strip()}")

    return result.stdout.strip()


def run_code(*command: str) -> tuple[int, str]:
    """Runs a command that is allowed to fail: returns its exit code and output."""
    result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT, env=environment())

    return result.returncode, result.stdout + result.stderr


def run_showing(*command: str, keep=lambda line: True) -> tuple[int, str]:
    """Runs a command and shows its output as it appears (only the lines `keep` accepts)."""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=ROOT, env=environment())
    output = []

    for line in process.stdout:
        output.append(line)

        if line.strip() and keep(line):
            live.say(line.strip(), "▸")

    return process.wait(), "".join(output)


def succeeds(*command: str) -> bool:
    return subprocess.run(command, capture_output=True, cwd=ROOT, env=environment()).returncode == 0


def wait_until(condition, timeout: float, interval: float = 1) -> float | None:
    """Seconds until the condition holds, or None if it does not within the timeout."""
    start = time.monotonic()

    while time.monotonic() - start < timeout:
        if condition():
            return time.monotonic() - start

        time.sleep(interval)

    return None


# --- The service through the balancer ----------------------------------------

@dataclass
class Response:
    status: int                     # 0 if nobody answered
    headers: dict = field(default_factory=dict)
    body: dict | None = None
    at: float = 0                   # when it was sent

    @property
    def instance(self) -> str:
        return self.headers.get("x-instance-id", "")


def lowercase(headers) -> dict:
    """HTTP header names are case-insensitive: they are compared in lowercase."""
    return {name.lower(): value for name, value in headers.items()}


def get(path: str, base: str = BALANCER, timeout: float = 3, show: bool = False) -> Response:
    """One call to the service. With `show`, it is also printed as it happens."""
    response = fetch(path, base, timeout)

    if show:
        live.request(response, path)

    return response


def fetch(path: str, base: str, timeout: float) -> Response:
    sent = time.time()

    try:
        with urllib.request.urlopen(base + path, timeout=timeout) as response:
            return Response(response.status, lowercase(response.headers), json.loads(response.read()), sent)
    except urllib.error.HTTPError as error:
        return Response(error.code, lowercase(error.headers), None, sent)
    except (urllib.error.URLError, OSError, ValueError):
        return Response(0, at=sent)


class Traffic:
    """Sends a request every `interval` seconds in the background and keeps every response."""

    def __init__(self, path: str = "/orders", interval: float = 0.25, show: bool = True) -> None:
        self.path = path
        self.interval = interval
        self.show = show
        self.responses: list[Response] = []
        self._running = threading.Event()
        self._thread = threading.Thread(target=self._send, daemon=True)

    def start(self) -> None:
        self._running.set()
        self._thread.start()

    def stop(self) -> list[Response]:
        self._running.clear()
        self._thread.join()

        return self.responses

    def _send(self) -> None:
        while self._running.is_set():
            self.responses.append(get(self.path, show=self.show))
            time.sleep(self.interval)


def success_rate(responses: list[Response]) -> float:
    return sum(r.status == 200 for r in responses) / len(responses) if responses else 0


# --- Containers and data -----------------------------------------------------

def api_containers() -> list[str]:
    """Full ids of the API containers that are running."""
    return run("docker", "compose", "ps", "-q", "api").split()


def announce_instances() -> None:
    """Tells which instances are running, and remembers their names to show them in the calls."""
    current = {}

    for container in api_containers():
        current[short(container)] = live.readable(run("docker", "inspect", "-f", "{{.Name}}", container).lstrip("/"))

    live.names.update(current)
    live.say("instancias de la API: " + ", ".join(f"{name} ({id})" for id, name in current.items()), "🧭")


def short(container: str) -> str:
    """The instance id the API reports is the short container id."""
    return container[:12]


def volume_file() -> str:
    return run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "cat", "/data/orders.json", check=False)


def volume_hash() -> str:
    output = run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "sha256sum", "/data/orders.json", check=False)

    return output.split()[0] if output else ""


def corrupt_data() -> None:
    run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "sh", "-c", "echo corrupted > /data/orders.json")


def delete_data() -> None:
    run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "rm", "/data/orders.json")


def current_tag() -> str:
    history = ROOT / ".deploy-history"

    return history.read_text().split()[-1] if history.exists() else "dev"


def wait_until_balancer_uses(containers: list[str], timeout: float = 90) -> bool:
    wanted = {short(c) for c in containers}

    return wait_until(lambda: wanted <= {get("/health").instance for _ in range(10)}, timeout, 2) is not None


# --- HAProxy log -------------------------------------------------------------

def down_events(log: str) -> list[float]:
    """When HAProxy took an API server out of the rotation, as epoch seconds (the log is in UTC)."""
    events = []

    for line in log.splitlines():
        if "Server api/" in line and "DOWN" in line:
            match = re.match(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?)", line)

            if match:
                events.append(datetime.fromisoformat(match.group(1)).replace(tzinfo=timezone.utc).timestamp())

    return events


def haproxy_down_events(since: float) -> list[float]:
    log = run("docker", "compose", "logs", "--no-log-prefix", "-t", "--since", str(int(since)), "haproxy", check=False)

    return down_events(log)
