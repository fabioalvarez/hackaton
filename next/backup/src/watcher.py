"""Backs up the data when it is new, and brings it back when it is lost or altered.

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
        version = get_data_version(self.data_file)

        if version is None:
            self.recover_lost_data()
            return

        if not self.has_backup(version):
            self.back_up(version)
            
        elif self.is_altered(version):
            self.restore(version, "content changed without changing the version")

        self.remember_as_latest(version)

    # --- What to do ------------------------------------------------------------

    def recover_lost_data(self) -> None:
        """The data is missing or invalid: bring back the last valid version."""
        version = self.latest_version()

        if version and self.has_backup(version):
            self.restore(version, "data file missing or invalid")
        else:
            log("error", detail="data file missing or invalid, and there is no backup to restore")

    def back_up(self, version: str) -> None:
        shutil.copyfile(self.data_file, self.copy_path(version))
        self.hash_path(version).write_text(sha256(self.copy_path(version)))

        log("backup", version, "new version backed up")

    def restore(self, version: str, reason: str) -> None:
        start = time.monotonic()

        try:
            replace_file(self.copy_path(version), self.data_file)
        except OSError as error:
            log("restore_failed", version, f"{reason}: {error}")
            return

        log("restore_ok", version, f"{reason} (took {time.monotonic() - start:.1f}s)")

    # --- Questions -------------------------------------------------------------

    def has_backup(self, version: str) -> bool:
        return self.copy_path(version).exists()

    def is_altered(self, version: str) -> bool:
        """True if the data differs from the backup of the same version."""
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
