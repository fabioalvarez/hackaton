"""Small file helpers shared by the watcher."""

import hashlib
import os
import shutil
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_text(path: Path) -> str:
    """Content of a text file, stripped; empty if the file does not exist."""
    return path.read_text().strip() if path.exists() else ""


def replace_file(source: Path, target: Path) -> None:
    """Copies `source` over `target` in one step, so readers never see half a file."""
    tmp = target.with_name(target.name + ".tmp")
    shutil.copyfile(source, tmp)
    os.replace(tmp, target)
