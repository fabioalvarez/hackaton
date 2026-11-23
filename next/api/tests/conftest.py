"""Shared fixtures: test data, a data file and a factory of app instances."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from next.main import create_app
from next.settings import Settings

@pytest.fixture
def sample_data() -> dict:
    """The data the service starts with in every test: 6 orders and their version."""
    return {
        "data_version": "data-v1",
        "orders": [
            {"id": "ORD-001", "zone": "North", "status": "in_transit"},
            {"id": "ORD-002", "zone": "Center", "status": "delivered"},
            {"id": "ORD-003", "zone": "South", "status": "pending"},
            {"id": "ORD-004", "zone": "West", "status": "in_transit"},
            {"id": "ORD-005", "zone": "East", "status": "delivered"},
            {"id": "ORD-006", "zone": "Center", "status": "preparing"},
        ],
    }


@pytest.fixture
def data_file(tmp_path: Path, sample_data: dict) -> Path:
    """Data file of the test, in a temporary folder so tests can alter it freely."""
    path = tmp_path / "orders.json"
    path.write_text(json.dumps(sample_data))
    return path


@pytest.fixture
def make_client(data_file: Path):
    """Builds an instance of the service reading `data_file`, like a container would."""

    def _make(instance_id: str = "instance-A") -> TestClient:
        settings = Settings(data_path=data_file, instance_id=instance_id, service_name="Test Service")
        return TestClient(create_app(settings), raise_server_exceptions=False)

    return _make


@pytest.fixture
def client(make_client) -> TestClient:
    return make_client("instance-A")
