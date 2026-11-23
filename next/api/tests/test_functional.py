"""Functional requirements: one test per RF (RF-01 to RF-05)."""

import pytest


def test_rf01_orders_returns_all_orders(client, sample_data):
    assert client.get("/orders").json()["orders"] == sample_data["orders"]


def test_rf02_orders_response_includes_the_data_version(client, sample_data):
    assert client.get("/orders").headers["X-Data-Version"] == sample_data["data_version"]


def test_rf02_the_version_is_not_repeated_in_the_body(client):
    assert "data_version" not in client.get("/orders").json()


def test_rf03_home_is_an_html_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Nodo Ruta" in response.text


def test_rf03_home_shows_the_service_and_the_instance_that_served_it(client):
    page = client.get("/").text

    assert "Test Service" in page
    assert "instance-A" in page


def test_rf03_home_links_to_the_other_pages(client):
    page = client.get("/").text

    assert 'href="/orders"' in page
    assert 'href="/health"' in page


def test_rf03_home_only_confirms_the_service_and_shows_no_data(client):
    page = client.get("/").text

    assert "ORD-001" not in page
    assert "data_version" not in page


def test_rf04_health_is_ok(client, sample_data):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["X-Data-Version"] == sample_data["data_version"]


@pytest.mark.parametrize("path", ["/", "/health", "/orders"])
def test_rf05_response_has_instance_id(client, path):
    assert client.get(path).headers["X-Instance-Id"] == "instance-A"


def test_rf05_each_instance_reports_its_own_id(make_client):
    a, b = make_client("instance-A"), make_client("instance-B")

    assert a.get("/orders").headers["X-Instance-Id"] == "instance-A"
    assert b.get("/orders").headers["X-Instance-Id"] == "instance-B"
