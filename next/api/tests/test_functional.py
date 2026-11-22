"""Functional requirements: one test per RF (RF-01 to RF-05)."""

import pytest


def test_rf01_orders_returns_all_orders(client, sample_data):
    assert client.get("/orders").json()["orders"] == sample_data["orders"]


def test_rf02_orders_includes_data_version(client, sample_data):
    assert client.get("/orders").json()["data_version"] == sample_data["data_version"]


def test_rf03_home_lists_routes(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"service": "Test Service", "routes": ["/health", "/orders"]}


def test_rf04_health_is_ok(client, sample_data):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "data_version": sample_data["data_version"]}


@pytest.mark.parametrize("path", ["/", "/health", "/orders"])
def test_rf05_response_has_instance_id(client, path):
    assert client.get(path).headers["X-Instance-Id"] == "instance-A"


def test_rf05_each_instance_reports_its_own_id(make_client):
    a, b = make_client("instance-A"), make_client("instance-B")

    assert a.get("/orders").headers["X-Instance-Id"] == "instance-A"
    assert b.get("/orders").headers["X-Instance-Id"] == "instance-B"
