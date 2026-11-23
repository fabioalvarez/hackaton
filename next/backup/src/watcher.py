"""Backs up the data when it is new or has changed, and brings it back when it is lost.

Backups live in `backup_dir`:
    orders-<version>.json    copy of the data of that version
    orders-<version>.sha256  hash of that copy
    latest                   last valid version seen
"""

import shutil
import time
from pathlib import Path

from logs import log
from settings import Settings
from utils import read_text, replace_file, sha256
from validation import get_data_version


class Watcher:
    def __init__(self, settings: Settings) -> None:
        self.data_file = settings.data_file
        self.backup_dir = settings.backup_dir

    def check(self) -> None:
        """Looks at the data once and does what is needed."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        log("starting backup process", level="debug")

        version = get_data_version(self.data_file)

        if version is None:
            self.recover_lost_data()
            return

        if not self.has_backup(version):
            log(f"new data version {version}, starting backup")
            self.back_up(version)

        elif self.differs_from_backup(version):
            log(f"data is different from the backup of {version}, starting backup")
            self.back_up(version)

        else:
            log(f"data file is the same as the backup of {version}, no backup is required", level="debug")

        self.remember_as_latest(version)

    # --- What to do ------------------------------------------------------------

    def recover_lost_data(self) -> None:
        """The data is missing or invalid: bring back the last valid version."""
        version = self.latest_version()

        if version and self.has_backup(version):
            log(f"data file is missing or invalid, starting restore of {version}")
            self.restore(version)
        else:
            log("data file is missing or invalid and there is no backup to restore", level="error")

    def back_up(self, version: str) -> None:
        shutil.copyfile(self.data_file, self.copy_path(version))
        
        self.hash_path(version).write_text(sha256(self.copy_path(version)))

        log("backup done")

    def restore(self, version: str) -> None:
        start = time.monotonic()

        try:
            replace_file(self.copy_path(version), self.data_file)
        except OSError as error:
            log(f"restore failed: {error}", level="error")
            return

        log(f"restore done in {time.monotonic() - start:.1f}s")

    # --- Questions -------------------------------------------------------------

    def has_backup(self, version: str) -> bool:
        return self.copy_path(version).exists()

    def differs_from_backup(self, version: str) -> bool:
        """True if the data is not the same as the backup of its version."""
        backup_hash = read_text(self.hash_path(version)) or sha256(self.copy_path(version))

        return sha256(self.data_file) != backup_hash

    def latest_version(self) -> str:
        return read_text(self.latest_path())

    def remember_as_latest(self, version: str) -> None:
        self.latest_path().write_text(version)

    # --- Paths -----------------------------------------------------------------

    def copy_path(self, version: str) -> Path:
        return self.backup_dir / f"orders-{version}.json"

    def hash_path(self, version: str) -> Path:
        return self.backup_dir / f"orders-{version}.sha256"

    def latest_path(self) -> Path:
        return self.backup_dir / "latest"
