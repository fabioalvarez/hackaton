"""Backup watcher (QA-02): runs one check of the watcher against temporary folders."""

import json
from pathlib import Path

import pytest

from settings import Settings
from watcher import Watcher

DATA = {
    "data_version": "data-v1",
    "orders": [
        {"id": "ORD-001", "zone": "North", "status": "in_transit"},
        {"id": "ORD-002", "zone": "Center", "status": "delivered"},
    ],
}


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    path = tmp_path / "orders.json"
    path.write_text(json.dumps(DATA))
    return path


@pytest.fixture
def backup_dir(tmp_path: Path) -> Path:
    return tmp_path / "backups"


@pytest.fixture
def check(data_file, backup_dir, capsys):
    """Runs one check of the watcher and returns the events it logged."""
    watcher = Watcher(Settings(data_file, backup_dir))

    def _check() -> list[dict]:
        capsys.readouterr()
        watcher.check()

        return [json.loads(line) for line in capsys.readouterr().out.splitlines()]

    return _check


def test_new_version_is_backed_up_with_its_version_in_the_name(check, backup_dir, data_file):
    events = check()

    assert [e["event"] for e in events] == ["backup"]
    assert (backup_dir / "orders-data-v1.json").read_text() == data_file.read_text()
    assert (backup_dir / "latest").read_text().strip() == "data-v1"


def test_nothing_happens_while_the_data_is_unchanged(check):
    check()

    assert check() == []


def test_a_new_version_gets_its_own_backup_and_keeps_the_old_one(check, backup_dir, data_file):
    check()
    data_file.write_text(json.dumps({**DATA, "data_version": "data-v2"}))
    check()

    assert (backup_dir / "orders-data-v1.json").exists()
    assert (backup_dir / "orders-data-v2.json").exists()
    assert (backup_dir / "latest").read_text().strip() == "data-v2"


def test_missing_file_is_restored(check, data_file):
    check()
    original = data_file.read_text()
    data_file.unlink()

    assert [e["event"] for e in check()] == ["restore_ok"]
    assert data_file.read_text() == original


@pytest.mark.parametrize("content", ["not json", json.dumps({"orders": []}), "{}"])
def test_invalid_file_is_restored(check, data_file, content):
    check()
    original = data_file.read_text()
    data_file.write_text(content)

    assert [e["event"] for e in check()] == ["restore_ok"]
    assert data_file.read_text() == original


def test_content_changed_without_changing_the_version_is_restored(check, data_file):
    check()
    original = data_file.read_text()
    altered = {**DATA, "orders": [{"id": "ORD-999", "zone": "North", "status": "pending"}]}
    data_file.write_text(json.dumps(altered))

    assert [e["event"] for e in check()] == ["restore_ok"]
    assert data_file.read_text() == original


def test_restores_the_latest_version_after_a_new_one_was_backed_up(check, data_file):
    check()
    v2 = json.dumps({**DATA, "data_version": "data-v2"})
    data_file.write_text(v2)
    check()
    data_file.unlink()
    check()

    assert data_file.read_text() == v2


def test_without_a_backup_nothing_is_invented(check, data_file):
    data_file.unlink()

    assert [e["event"] for e in check()] == ["error"]
    assert not data_file.exists()


def test_unsafe_version_is_not_accepted(check, backup_dir, data_file):
    data_file.write_text(json.dumps({**DATA, "data_version": "../../evil"}))

    assert [e["event"] for e in check()] == ["error"]
    assert not list(backup_dir.glob("orders-*"))
