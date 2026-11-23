"""Follows what the environment does while a check runs, and tells it in words.

Three sources: docker events (containers that start, stop or become healthy), the HAProxy log
(instances that enter or leave the rotation) and the log of the backup watcher.
"""

import json
import re
import subprocess
import threading
from pathlib import Path

import live

SERVICES = ("next-api", "next-haproxy", "next-backup")


def describe_event(event: str) -> tuple[str, str] | None:
    """A docker event (`action|container name`) as an icon and a sentence, or None if it is noise."""
    action, _, name = event.strip().partition("|")

    if not name.startswith(SERVICES):
        return None

    container = live.readable(name)
    sentences = {
        "create": ("📦", f"{container} creado"),
        "start": ("🟢", f"{container} arrancó"),
        "die": ("🔻", f"{container} se detuvo"),
        "destroy": ("🗑️ ", f"{container} eliminado"),
        "health_status: healthy": ("💚", f"{container} está sano"),
        "health_status: unhealthy": ("💔", f"{container} dejó de estar sano"),
    }

    return sentences.get(action)


def describe_haproxy(line: str) -> tuple[str, str] | None:
    """A line of the HAProxy log about its servers, or None for the lines about requests."""
    match = re.match(r"\s*Server api/\w+(?: \('api'\))? (.*)", line)

    if not match:
        return None

    rest = match.group(1)

    # HAProxy names its slots api1, api2... which are not the names of the containers, so they are not shown.
    if "going DOWN for maintenance" in rest:
        return "🔻", "HAProxy: una instancia ya no existe, deja de recibir solicitudes"
    if "is DOWN" in rest:
        reason = re.search(r"reason: ([^,]+)", rest)
        return "🔻", f"HAProxy: saca una instancia de la rotación ({reason.group(1) if reason else 'sin respuesta'})"
    if "is UP/READY" in rest:
        return "🔍", "HAProxy: encontró una instancia nueva y la está comprobando"
    if "is UP" in rest:
        return "🟢", "HAProxy: una instancia responde, entra a la rotación"

    return None


def describe_backup(line: str) -> tuple[str, str] | None:
    """A line of the backup watcher: what it did, not what it checked."""
    try:
        log = json.loads(line)
    except ValueError:
        return None

    return {"info": ("💾", f"vigilante: {log['detail']}"), "error": ("⚠️ ", f"vigilante: {log['detail']}")}.get(log.get("level"))


class Watching:
    """`with Watching(folder):` shows what the environment does until the block ends."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        self.processes: list[subprocess.Popen] = []

    def __enter__(self):
        self.follow(["docker", "events", "--filter", "type=container", "--filter", "label=com.docker.compose.project=next",
                     "--format", "{{.Action}}|{{.Actor.Attributes.name}}"], describe_event)
        self.follow(["docker", "compose", "logs", "-f", "--tail", "0", "--no-log-prefix", "haproxy"], describe_haproxy)
        self.follow(["docker", "compose", "logs", "-f", "--tail", "0", "--no-log-prefix", "backup"], describe_backup)

        return self

    def __exit__(self, *error) -> None:
        for process in self.processes:
            process.terminate()

    def follow(self, command: list[str], describe) -> None:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, cwd=self.folder)
        self.processes.append(process)

        def read() -> None:
            for line in process.stdout:
                described = describe(line)

                if described:
                    live.say(described[1], described[0])

        threading.Thread(target=read, daemon=True).start()
