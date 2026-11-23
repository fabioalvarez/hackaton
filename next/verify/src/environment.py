"""The environment the checks look at and change: containers, data and the balancer."""

import re
from datetime import datetime, timezone

import live
from commands import run
from service import get, wait_until

VOLUME = "next_orders-data"
PROJECT_LABEL = "label=com.docker.compose.project=next"


# --- The API containers -----------------------------------------------------------

def api_containers() -> list[str]:
    """Full ids of the API containers that are running."""
    return run("docker", "compose", "ps", "-q", "api").split()


def short(container: str) -> str:
    """The instance id the API reports is the short container id."""
    return container[:12]


def name_of(container: str) -> str:
    """`api-1`, for example; the short id if it is not known."""
    return live.names.get(short(container), short(container))


def announce_instances() -> None:
    """Tells which instances are running, and remembers their names to show them in the calls."""
    current = {short(c): live.readable(run("docker", "inspect", "-f", "{{.Name}}", c).lstrip("/")) for c in api_containers()}

    live.names.update(current)
    live.say("instancias de la API: " + ", ".join(f"{name} ({id})" for id, name in current.items()), "🧭")


def wait_until_balancer_uses(containers: list[str], timeout: float = 90) -> bool:
    """Healthy is not enough: the balancer must already be sending traffic to them."""
    wanted = {short(c) for c in containers}

    return wait_until(lambda: wanted <= {get("/health").instance for _ in range(10)}, timeout, 2) is not None


def restore_replicas() -> None:
    """Brings the service back to its 2 replicas and waits until the balancer uses them."""
    run("docker", "compose", "up", "-d", "--no-deps", "--wait", "api")
    wait_until_balancer_uses(api_containers())


def start_from_a_working_service() -> None:
    """Every scenario starts with 2 replicas that the balancer is already using."""
    if len(api_containers()) < 2:
        restore_replicas()

    wait_until_balancer_uses(api_containers())
    announce_instances()


def project_resources() -> list[str]:
    """Containers, volumes and networks of the project that still exist."""
    containers = run("docker", "ps", "-a", "-q", "--filter", PROJECT_LABEL).split()
    volumes = run("docker", "volume", "ls", "-q", "--filter", PROJECT_LABEL).split()
    networks = run("docker", "network", "ls", "-q", "--filter", PROJECT_LABEL).split()

    return containers + volumes + networks


# --- The data ---------------------------------------------------------------------

def volume_file() -> str:
    return run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "cat", "/data/orders.json", check=False)


def volume_hash() -> str:
    output = run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "sha256sum", "/data/orders.json", check=False)

    return output.split()[0] if output else ""


def corrupt_data() -> None:
    run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "sh", "-c", "echo corrupted > /data/orders.json")


def delete_data() -> None:
    run("docker", "run", "--rm", "-v", f"{VOLUME}:/data", "alpine", "rm", "/data/orders.json")


# --- The HAProxy log --------------------------------------------------------------

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


def seconds_until_haproxy_removed(instance_killed_at: float) -> float | None:
    """How long after the kill HAProxy took the instance out of the rotation; None if it did not."""
    events = [e for e in haproxy_down_events(instance_killed_at - 1) if e >= instance_killed_at - 1]

    return max(0.0, min(events) - instance_killed_at) if events else None
