"""What is shown on the terminal while the checks run: the calls, what happens in the
environment, and the verdict of each check."""

import json
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

names: dict[str, str] = {}      # instance id -> readable name, for example `api-1`

COLORS = {"green": 32, "red": 31, "yellow": 33, "cyan": 36, "dim": 2, "bold": 1}
SERVICES = ("next-api", "next-haproxy", "next-backup")
STARTS_A_STEP = ("▶", "⚡", "🚀", "♻️")   # these lines are preceded by an empty line, to separate the steps
_lock = threading.Lock()


# --- Printing ----------------------------------------------------------------

def paint(text: str, color: str) -> str:
    return f"\033[{COLORS[color]}m{text}\033[0m" if sys.stdout.isatty() else text


def say(text: str, icon: str = " ", color: str | None = None) -> None:
    """One line with the time, so the order of what happens can be followed."""
    clock = paint(datetime.now().strftime("%H:%M:%S"), "dim")
    line = f"{clock}  {icon} {paint(text, color) if color else text}"

    with _lock:
        print(("\n" if icon in STARTS_A_STEP else "") + line, flush=True)


def heading(text: str) -> None:
    with _lock:
        print(f"\n{paint('━━ ' + text, 'bold')}", flush=True)


def scenario(ids: str, title: str, criterion: str) -> None:
    """The start of a scenario, one level below the headings of the two groups of requirements."""
    with _lock:
        print(f"\n{paint('── ' + ids + ' · ' + title, 'bold')}", flush=True)
        print(paint(f"   Criterio: {criterion}", "cyan"), flush=True)


def request(response, path: str) -> None:
    """One call to the API: what was asked, what came back, and who answered."""
    who = names.get(response.instance, response.instance)

    if response.status == 200:
        say(f"GET {path:<8} 200  atendió {who}", "✅")
    elif response.status == 0:
        say(f"GET {path:<8} sin respuesta", "❌", "red")
    else:
        say(f"GET {path:<8} {response.status}  atendió {who or 'nadie'}", "❌", "red")


def verdict(result) -> None:
    icon, color = ("✅", "green") if result.passed else ("❌", "red")
    say(f"{result.id}: {result.measured}", icon, color)


def pause(message: str) -> None:
    """Waits for Enter, so the person presenting can explain before the next scenario."""
    if sys.stdin.isatty():
        input(paint(f"\n{message} [Enter] ", "yellow"))


# --- What happens in the environment, in words ---------------------------------

def readable(container: str) -> str:
    return container.removeprefix("next-")


def describe_event(event: str) -> tuple[str, str] | None:
    """A docker event (`action|container name`) as an icon and a sentence, or None if it is noise."""
    action, _, name = event.strip().partition("|")

    if not name.startswith(SERVICES):
        return None

    sentences = {
        "create": ("📦", f"{readable(name)} creado"),
        "start": ("🟢", f"{readable(name)} arrancó"),
        "die": ("🔻", f"{readable(name)} se detuvo"),
        "destroy": ("🗑️ ", f"{readable(name)} eliminado"),
        "health_status: healthy": ("💚", f"{readable(name)} está sano"),
        "health_status: unhealthy": ("💔", f"{readable(name)} dejó de estar sano"),
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


# --- Watching the environment while a check runs ------------------------------

class Watching:
    """Follows docker events, the HAProxy log and the backup watcher, and shows what they report."""

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
                    say(described[1], described[0])

        threading.Thread(target=read, daemon=True).start()
