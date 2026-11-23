"""Running commands the way `make` does: from the `next/` folder, with TAG set to the version that runs.

Without TAG, docker compose would think the image changed and recreate every container.
"""

import os
import re
import subprocess
from pathlib import Path

import live

ROOT = Path(__file__).resolve().parents[2]      # the `next/` folder


def make(*targets: str) -> list[str]:
    """The `make` command. It lives in the root of the repository, one level above `next/`."""
    return ["make", "-C", str(ROOT.parent), *targets]


# --- The versions that were deployed ---------------------------------------------

def deployed_versions() -> list[str]:
    """One per line in `.deploy-history`; the last one is the version that runs."""
    history = ROOT / ".deploy-history"

    return history.read_text().split() if history.exists() else []


def current_tag() -> str:
    versions = deployed_versions()

    return versions[-1] if versions else "dev"


def next_version() -> str:
    """The version a new deployment gets: v1, v2, v3... after the last one that was deployed."""
    numbers = [int(tag[1:]) for tag in deployed_versions() if re.fullmatch(r"v\d+", tag)]

    return f"v{max(numbers, default=0) + 1}"


# --- Running ---------------------------------------------------------------------

def environment() -> dict:
    return {**os.environ, "TAG": current_tag()}


def run(*command: str, check: bool = True) -> str:
    """Runs a command and returns its output. If it fails, raises (unless `check` is False)."""
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
