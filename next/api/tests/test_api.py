"""One test per functional requirement (RF-01 to RF-05) plus error cases."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from next.main import create_app
from next.settings import Settings

SAMPLE = Path(__file__).parent.parent / "data" / "orders.json"


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    path = tmp_path / "orders.json"
    shutil.copy(SAMPLE, path)
    return path


@pytest.fixture
def client(data_file: Path) -> TestClient:
    settings = Settings(data_path=data_file, instance_id="instance-A", service_name="Test Service")
    return TestClient(create_app(settings))


def test_orders_returns_all_orders(client):  # RF-01
    body = client.get("/orders").json()
    assert len(body["orders"]) == 6


def test_orders_includes_data_version(client):  # RF-02
    assert client.get("/orders").json()["data_version"] == "data-v1"


def test_home_lists_routes(client):  # RF-03
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"service": "Test Service", "routes": ["/health", "/orders"]}


def test_health_is_ok(client):  # RF-04
    assert client.get("/health").json() == {"status": "ok", "data_version": "data-v1"}


@pytest.mark.parametrize("path", ["/", "/health", "/orders", "/missing"])
def test_every_response_has_instance_header(client, path):  # RF-05
    assert client.get(path).headers["X-Instance-Id"] == "instance-A"


def test_unknown_route_is_404(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.json() == {"error": "Route not found"}


def test_wrong_method_is_405(client):
    assert client.post("/orders").status_code == 405


def test_docs_are_disabled(client):
    assert client.get("/docs").status_code == 404


@pytest.mark.parametrize("path", ["/health", "/orders"])
def test_missing_data_file_is_503(client, data_file, path):
    data_file.unlink()
    response = client.get(path)
    assert response.status_code == 503
    assert response.json() == {"status": "data_error"}
    assert response.headers["X-Instance-Id"] == "instance-A"


def test_invalid_data_is_503(client, data_file):
    data_file.write_text(json.dumps({"data_version": "", "orders": []}))
    assert client.get("/health").status_code == 503


def test_new_data_version_is_served_without_restart(client, data_file):
    data_file.write_text(json.dumps({"data_version": "data-v2", "orders": []}))
    assert client.get("/orders").json()["data_version"] == "data-v2"
