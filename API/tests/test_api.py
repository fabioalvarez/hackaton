"""Pruebas de la API, alineadas con el plan de pruebas (PR-01, PR-05)."""
from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_pedidos_devuelve_6_con_version():
    # RF-01: responde los 6 pedidos. RF-02: incluye la versión.
    r = client.get("/pedidos")
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["count"] == 6
    assert len(cuerpo["pedidos"]) == 6
    assert cuerpo["version"] == "v1"


def test_inicio_responde():
    # RF-03: página de inicio.
    r = client.get("/")
    assert r.status_code == 200
    assert "Nodo Ruta" in r.text


def test_health_ok():
    # RF-04: salud "ok".
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_header_instance_id_en_toda_respuesta():
    # RF-05: cada respuesta indica la instancia que la atendió.
    for ruta in ("/", "/pedidos", "/health"):
        r = client.get(ruta)
        assert r.headers.get("X-Instance-Id") == "test-instance"


def test_version_defectuosa_falla_health(monkeypatch):
    # A9 / QA-04 (PR-05): con FAIL_HEALTH la salud falla -> habilita rollback.
    monkeypatch.setattr(main.settings, "fail_health", True)
    r = client.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "fail"
    # Aun fallando, conserva el header de instancia.
    assert r.headers.get("X-Instance-Id") == "test-instance"
