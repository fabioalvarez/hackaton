"""Configuration, read only from environment variables."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_file: Path
    backup_dir: Path
    interval: float = 5  # seconds between checks

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_file=Path(os.environ.get("DATA_FILE", "/data/orders.json")),
            backup_dir=Path(os.environ.get("BACKUP_DIR", "/backups")),
            interval=float(os.environ.get("INTERVAL", "5")),
        )
