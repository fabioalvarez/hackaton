"""What is printed while the checks run. Only printing: it knows nothing about docker or the service."""

import sys
import threading
from datetime import datetime

names: dict[str, str] = {}      # instance id -> readable name, for example `api-1`

COLORS = {"green": 32, "red": 31, "yellow": 33, "cyan": 36, "dim": 2, "bold": 1}
STARTS_A_STEP = ("▶", "⚡", "🚀", "♻️")   # these lines get an empty line before them, to separate the steps
_lock = threading.Lock()


def paint(text: str, color: str) -> str:
    return f"\033[{COLORS[color]}m{text}\033[0m" if sys.stdout.isatty() else text


def readable(container: str) -> str:
    """`next-api-1` -> `api-1`"""
    return container.removeprefix("next-")


# --- Lines with the time ---------------------------------------------------------

def say(text: str, icon: str = " ", color: str | None = None) -> None:
    clock = paint(datetime.now().strftime("%H:%M:%S"), "dim")
    line = f"{clock}  {icon} {paint(text, color) if color else text}"

    with _lock:
        print(("\n" if icon in STARTS_A_STEP else "") + line, flush=True)


def step(text: str) -> None:
    say(text, "▶")


def stimulus(text: str) -> None:
    """The thing that is done to the environment to see how it reacts."""
    say(text, "⚡", "yellow")


def deploying(text: str, color: str | None = None) -> None:
    say(text, "🚀", color)


def restoring(text: str) -> None:
    say(text, "♻️")


def found(text: str) -> None:
    """Something that was looked at, not changed."""
    say(text, "🔎")


# --- Headings and verdicts -----------------------------------------------------------

def heading(text: str) -> None:
    with _lock:
        print(f"\n{paint('━━ ' + text, 'bold')}", flush=True)


def scenario(requirements) -> None:
    """The start of a scenario: its requirements and their criteria."""
    with _lock:
        print(f"\n{paint('── ' + ' y '.join(r.id for r in requirements), 'bold')}", flush=True)

        for requirement in requirements:
            print(f"\n{paint(f'   {requirement.id} · {requirement.title}', 'bold')}", flush=True)
            print(paint(f"   Criterio: {requirement.criterion}", "cyan"), flush=True)

        print(flush=True)


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
