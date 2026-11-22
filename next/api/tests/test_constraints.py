"""Constraints (CT-01, CT-02) and configuration (A7): pass or fail checks."""

from pathlib import Path

import pytest

from next.routes import router
from next.settings import Settings

API_DIR = Path(__file__).parent.parent
PROJECT_DIR = API_DIR.parent


# --- CT-01 · No secrets in the image or the repository --------------------------


def test_ct01_settings_have_no_secret_fields():
    names = " ".join(Settings.model_fields)

    for word in ("password", "secret", "token", "key", "credential"):
        assert word not in names


def test_ct01_dotenv_is_kept_out_of_git():
    assert ".env" in (PROJECT_DIR / ".gitignore").read_text().split()


def test_ct01_dotenv_is_outside_the_docker_build_context():
    assert not (API_DIR / ".env").exists()


def test_ct01_data_is_outside_the_docker_build_context():
    found = [p for p in API_DIR.rglob("orders*.json") if ".venv" not in p.parts]

    assert found == []


# --- CT-02 · Minimal exposure ---------------------------------------------------


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_ct02_interactive_docs_are_disabled(client, path):
    assert client.get(path).status_code == 404


def test_ct02_service_is_read_only(client):
    methods = {method for route in router.routes for method in route.methods}

    assert methods <= {"GET", "HEAD"}


@pytest.mark.parametrize("method", ["post", "put", "patch", "delete"])
def test_ct02_write_methods_are_rejected(client, method):
    assert getattr(client, method)("/orders").status_code == 405


def test_ct02_only_the_expected_routes_exist():
    paths = {route.path for route in router.routes}

    assert paths == {"/", "/health", "/orders"}


# --- A7 · Configuration comes from the environment ------------------------------


def test_a7_settings_are_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("PORT", "9090")
    monkeypatch.setenv("INSTANCE_ID", "from-env")

    settings = Settings()

    assert settings.port == 9090
    assert settings.instance_id == "from-env"


def test_a7_instance_id_defaults_to_hostname(monkeypatch):
    monkeypatch.delenv("INSTANCE_ID", raising=False)

    assert Settings().instance_id


def test_a7_invalid_value_fails_at_startup(monkeypatch):
    monkeypatch.setenv("PORT", "not-a-number")

    with pytest.raises(ValueError):
        Settings()
