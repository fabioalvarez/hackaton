"""Quality attributes that the API itself must satisfy (QA-01, QA-03, QA-04, QA-06).

QA-01 (failover), QA-02 (backup), QA-05 (deploy) and QA-07 (cost) depend on the
environment (nginx, Docker, backups) and are verified in the test plan, not here.
"""

import json
import logging

import pytest


# --- QA-01 · Availability: stateless instances, interchangeable -----------------


def test_qa01_instances_return_the_same_content(make_client):
    a, b = make_client("instance-A"), make_client("instance-B")

    assert a.get("/orders").json() == b.get("/orders").json()


# --- QA-03 · Durability: state lives outside the instance -----------------------


def test_qa03_recreated_instance_serves_the_same_data(make_client):
    before = make_client("instance-A").get("/orders").json()
    after = make_client("instance-A-recreated").get("/orders").json()

    assert after == before


def test_qa03_new_data_version_is_served_without_restart(client, data_file):
    data_file.write_text(json.dumps({"data_version": "new-version", "orders": []}))

    assert client.get("/orders").json()["data_version"] == "new-version"


# --- QA-04 · Recoverability: a defective version must fail its health check -----


def test_qa04_health_fails_when_data_file_is_missing(client, data_file):
    data_file.unlink()

    assert client.get("/health").status_code == 503


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        json.dumps({"orders": []}),
        json.dumps({"data_version": "", "orders": []}),
        json.dumps({"data_version": "v", "orders": [{"id": "1", "zone": "N", "status": "lost"}]}),
    ],
    ids=["not-json", "no-version", "empty-version", "invalid-status"],
)
def test_qa04_health_fails_when_data_is_invalid(client, data_file, content):
    data_file.write_text(content)

    assert client.get("/health").status_code == 503


@pytest.mark.parametrize("path", ["/health", "/orders"])
def test_qa04_data_error_response_and_instance_header(client, data_file, path):
    data_file.unlink()
    response = client.get(path)

    assert response.json() == {"status": "data_error"}
    assert response.headers["X-Instance-Id"] == "instance-A"


# --- QA-06 · Observability: every request traceable to an instance --------------


@pytest.fixture
def logs(caplog):
    caplog.set_level(logging.DEBUG, logger="next")
    return caplog


def request_logs(logs):
    return [r for r in logs.records if r.getMessage() == "request"]


def test_qa06_request_log_has_instance_and_request_data(client, logs, sample_data):
    client.get("/orders")
    fields = request_logs(logs)[0].fields

    assert fields["instance"] == "instance-A"
    assert fields["method"] == "GET"
    assert fields["path"] == "/orders"
    assert fields["status"] == 200
    assert fields["data_version"] == sample_data["data_version"]
    assert fields["ms"] >= 0


def test_qa06_every_request_is_traceable_to_an_instance(client, logs):
    paths = ["/", "/health", "/orders", "/missing"] * 5

    for path in paths:
        client.get(path)

    records = request_logs(logs)
    assert len(records) == len(paths)
    assert all(r.fields["instance"] == "instance-A" for r in records)


def test_qa06_health_ok_is_debug_and_health_failure_is_info(client, data_file, logs):
    client.get("/health")
    assert request_logs(logs)[0].levelno == logging.DEBUG

    data_file.unlink()
    client.get("/health")
    assert request_logs(logs)[1].levelno == logging.INFO


def test_qa06_data_error_logs_instance_path_and_cause(client, data_file, logs):
    data_file.unlink()
    client.get("/orders")
    record = next(r for r in logs.records if r.getMessage() == "data error")

    assert record.levelno == logging.ERROR
    assert record.fields["instance"] == "instance-A"
    assert record.fields["path"] == "/orders"
    assert "orders.json" in record.fields["cause"]


def test_qa06_unhandled_error_logs_where_it_happened(client, logs):
    @client.app.get("/boom")
    def boom():
        raise RuntimeError("boom")

    response = client.get("/boom")
    record = next(r for r in logs.records if r.getMessage() == "unhandled error")

    assert response.status_code == 500
    assert response.headers["X-Instance-Id"] == "instance-A"
    assert record.fields == {"instance": "instance-A", "method": "GET", "path": "/boom"}
    assert record.exc_info is not None
