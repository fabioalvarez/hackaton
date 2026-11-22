"""Calls to docker. Each function runs one command and returns what the deployment needs."""

import os
import subprocess
import urllib.request

SERVICE = "api"
IMAGE = "next-api"
BALANCER_URL = f"http://localhost:{os.environ.get('PORT', '8000')}/health"


def run(*command: str, tag: str = "", broken: bool = False) -> str:
    """Runs a command and returns its output. TAG and BREAK are how the Compose file knows the version."""
    env = {**os.environ, "TAG": tag, "BREAK": "1" if broken else ""}
    result = subprocess.run(command, capture_output=True, text=True, env=env)

    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(command)}\n{result.stderr.strip()}")

    return result.stdout.strip()


def running() -> list[str]:
    """Ids of the API containers that are up."""
    return run("docker", "compose", "ps", "-q", SERVICE).split()


def containers() -> list[str]:
    """Ids of the API containers, in any state."""
    return run("docker", "compose", "ps", "-a", "-q", SERVICE).split()


def image_of(container: str) -> str:
    return run("docker", "inspect", "-f", "{{.Config.Image}}", container)


def state_of(container: str) -> str:
    """`healthy`, `starting` or `unhealthy`; `restarting` or `exited` if the container cannot stay up."""
    status, health = run(
        "docker", "inspect", "-f",
        "{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
        container,
    ).split()

    return health if status == "running" else status


def logs_of(container: str, lines: int = 5) -> str:
    return run("docker", "logs", "--tail", str(lines), container)


def build(tag: str, broken: bool) -> None:
    run("docker", "compose", "build", SERVICE, tag=tag, broken=broken)


def start_next_to_the_current(total: int, tag: str) -> None:
    """Creates containers until there are `total`, without touching the ones that exist."""
    run("docker", "compose", "up", "-d", "--no-deps", "--no-recreate", "--scale", f"{SERVICE}={total}", SERVICE, tag=tag)


def instances_served(requests: int = 10) -> set[str]:
    """Ids of the instances that answer through the balancer, taken from the X-Instance-Id header."""
    served = set()

    for _ in range(requests):
        try:
            with urllib.request.urlopen(BALANCER_URL, timeout=2) as response:
                served.add(response.headers["X-Instance-Id"])
        except OSError:
            pass  # the balancer has no instance to answer yet

    return served


def remove(containers: list[str]) -> None:
    run("docker", "rm", "-f", *containers)


def image_tags() -> list[str]:
    return run("docker", "image", "ls", IMAGE, "--format", "{{.Tag}}").split()


def remove_image(tag: str) -> None:
    run("docker", "rmi", f"{IMAGE}:{tag}")
