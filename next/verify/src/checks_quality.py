"""Quality scenarios (QA-01 to QA-07). Each one causes the stimulus and measures the response,
telling what it does as it goes.

These checks change the environment: they kill and recreate containers, break the data, deploy
versions and take everything down. They leave it running at the end.
"""

import hashlib
import json
import time
from pathlib import Path

import live
from result import Result, covers
from system import (ROOT, Traffic, announce_instances, api_containers, corrupt_data, current_tag,
                    delete_data, get, haproxy_down_events, run, run_showing, short, success_rate,
                    volume_file, volume_hash, wait_until, wait_until_balancer_uses)

PROJECT_LABEL = "label=com.docker.compose.project=next"


def restore_replicas() -> None:
    """Brings the service back to its 2 replicas and waits until the balancer uses them."""
    run("docker", "compose", "up", "-d", "--no-deps", "--wait", "api")
    wait_until_balancer_uses(api_containers())


def start_from_a_working_service() -> None:
    """Every scenario starts with 2 replicas that the balancer is already using."""
    if len(api_containers()) < 2:
        restore_replicas()

    wait_until_balancer_uses(api_containers())
    announce_instances()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def seconds_text(seconds: float | None) -> str:
    return "no ocurrió" if seconds is None else f"{seconds:.1f} s"


# --- QA-01 and QA-06: an instance fails ---------------------------------------

@covers("QA-01", "QA-06")
def instance_failure() -> list[Result]:
    live.scenario("QA-01 y QA-06", "Una instancia se detiene con consultas en curso",
                  "≥ 99 % de solicitudes exitosas; HAProxy la saca en ≤ 10 s; la causa se encuentra con los logs en ≤ 120 s")
    start_from_a_working_service()

    before = api_containers()
    known = {short(c) for c in before}
    victim = live.names.get(short(before[0]), short(before[0]))

    live.say("empiezo a enviar una consulta cada 0,25 s a través del balanceador", "▶")
    traffic = Traffic()
    traffic.start()
    time.sleep(3)

    live.say(f"detengo la instancia {victim} de golpe (docker kill)", "⚡", "yellow")
    killed_at = time.time()
    run("docker", "kill", before[0])
    wait_until(lambda: haproxy_down_events(killed_at - 1), 60)
    time.sleep(5)
    responses = traffic.stop()

    live.say("levanto de nuevo la réplica para dejar el entorno completo", "♻️")
    restore_replicas()

    events = [e for e in haproxy_down_events(killed_at - 1) if e >= killed_at - 1]
    removed_after = max(0.0, min(events) - killed_at) if events else None
    rate = success_rate(responses)
    traced = [r for r in responses if r.status == 200]
    untraceable = [r for r in traced if r.instance not in known]

    qa01 = Result("QA-01", "Una instancia se detiene con consultas en curso",
                  "≥ 99 % de solicitudes exitosas; HAProxy deja de enviarle solicitudes en ≤ 10 s",
                  f"{rate:.1%} de {len(responses)} solicitudes; HAProxy la sacó en {seconds_text(removed_after)}",
                  rate >= 0.99 and removed_after is not None and removed_after <= 10,
                  [f"instancia detenida: {victim}"])

    qa06 = Result("QA-06", "Diagnosticar el incidente con los logs",
                  "instancia afectada identificada en ≤ 120 s; 100 % de las solicitudes asociadas a una instancia",
                  f"identificada en {seconds_text(removed_after)} (log de HAProxy: `Server api/... DOWN`); "
                  f"{len(traced) - len(untraceable)} de {len(traced)} solicitudes con instancia conocida",
                  removed_after is not None and removed_after <= 120 and not untraceable,
                  ["comandos de diagnóstico: `docker compose ps -a` y `docker compose logs haproxy`"])

    return [qa01, qa06]


# --- QA-02: the data is lost --------------------------------------------------

@covers("QA-02")
def data_loss() -> Result:
    live.scenario("QA-02", "Los datos se pierden",
                  "restaurados sin intervención en ≤ 5 min; versión y contenido idénticos al respaldo")
    start_from_a_working_service()

    original = volume_hash()
    version = json.loads(volume_file())["data_version"]
    backup = ROOT / "store" / "backups" / f"orders-{version}.json"
    live.say(f"el vigilante tiene un respaldo de la versión {version}; compruebo que es igual a los datos", "🔎")
    backed_up = wait_until(lambda: backup.exists() and sha256(backup) == original, 30)

    live.say("sigo consultando la API mientras se pierden los datos", "▶")
    traffic = Traffic()
    traffic.start()
    time.sleep(2)

    recovery = {}
    for cause, lose in (("archivo inválido", corrupt_data), ("archivo borrado", delete_data)):
        live.say(f"dejo los datos así: {cause}", "⚡", "yellow")
        lose()
        recovery[cause] = wait_until(lambda: volume_hash() == original, 300)
        live.say(f"los datos volvieron a ser idénticos al respaldo ({seconds_text(recovery[cause])})", "💾")
        time.sleep(3)

    traffic.stop()
    start_from_a_working_service()

    ok = backed_up is not None and all(s is not None and s <= 300 for s in recovery.values())

    return Result("QA-02", "Los datos se pierden",
                  "restaurados sin intervención en ≤ 5 min; versión y contenido idénticos al respaldo",
                  "; ".join(f"{cause}: {seconds_text(s)}" for cause, s in recovery.items())
                  + f"; coincide con el respaldo de {version}: {'sí' if backed_up is not None else 'no'}",
                  ok, [f"hash del respaldo = hash restaurado = {original[:16]}..."])


# --- QA-03: a container is recreated ------------------------------------------

@covers("QA-03")
def recreated_container() -> Result:
    live.scenario("QA-03", "Se recrea un contenedor del servicio",
                  "0 pedidos perdidos o modificados; misma versión antes y después")
    start_from_a_working_service()

    live.say("consulto los pedidos antes de tocar nada", "▶")
    before = get("/orders", show=True).body or {}

    victim = api_containers()[0]
    live.say(f"elimino el contenedor {live.names.get(short(victim), short(victim))} y dejo que se cree otro", "⚡", "yellow")
    traffic = Traffic()
    traffic.start()
    run("docker", "rm", "-f", victim)
    restore_replicas()
    traffic.stop()

    live.say("consulto los pedidos otra vez", "▶")
    announce_instances()
    after = get("/orders", show=True).body or {}
    lost = len(before.get("orders", [])) - len(after.get("orders", []))

    return Result("QA-03", "Se recrea un contenedor del servicio",
                  "0 pedidos perdidos o modificados; misma versión antes y después",
                  f"{lost} pedidos perdidos; versión {before.get('data_version')} → {after.get('data_version')}; "
                  f"contenido {'igual' if before == after else 'distinto'}",
                  before == after and lost == 0)


# --- QA-04: a defective version is deployed -----------------------------------

def deploy(tag: str, broken: bool = False) -> tuple[int, str]:
    command = ["python3", "deploy/src/main.py", tag] + (["--break"] if broken else [])

    return run_showing(*command)


@covers("QA-04")
def defective_version() -> Result:
    live.scenario("QA-04", "Se publica una versión que no funciona",
                  "servicio restablecido en ≤ 5 min con la versión anterior; 0 pedidos perdidos")
    start_from_a_working_service()

    good = f"verify-{int(time.time())}"
    live.say(f"primero despliego una versión buena ({good})", "🚀")
    good_code, _ = deploy(good)
    announce_instances()
    before = get("/orders", show=True).body

    live.say("ahora despliego una versión defectuosa, que no arranca, con consultas en curso", "🚀", "yellow")
    traffic = Traffic()
    traffic.start()
    time.sleep(3)
    started = time.monotonic()
    broken_code, output = deploy("verify-broken", broken=True)
    seconds = time.monotonic() - started
    time.sleep(5)
    responses = traffic.stop()

    live.say("compruebo que sigue corriendo la versión buena y que los datos no cambiaron", "🔎")
    after = get("/orders", show=True).body
    images = {run("docker", "inspect", "-f", "{{.Config.Image}}", c) for c in api_containers()}
    failed = sum(r.status != 200 for r in responses)
    kept = images == {f"next-api:{good}"} and current_tag() == good

    return Result("QA-04", "Se publica una versión que no funciona",
                  "servicio restablecido en ≤ 5 min con la versión anterior; 0 pedidos perdidos",
                  f"descartada en {seconds:.0f} s (salida {broken_code}); versión vigente {current_tag()}; "
                  f"{failed} solicitudes fallidas de {len(responses)}; datos {'iguales' if before == after else 'distintos'}",
                  good_code == 0 and broken_code == 1 and seconds <= 300 and kept and failed == 0 and before == after,
                  [f"despliegue bueno {good}: salida {good_code}", output.strip().splitlines()[-1]])


# --- QA-05 and QA-07: from scratch and back to nothing ------------------------

@covers("QA-05")
def clean_start() -> Result:
    live.scenario("QA-05", "Crear el despliegue completo desde cero",
                  "operativo con las 2 instancias en ≤ 10 min, con un solo comando")

    live.say("bajo todo el entorno (make down)", "⚡", "yellow")
    run("make", "down")

    live.say("lo levanto con un solo comando (make up)", "▶")
    started = time.monotonic()
    code, _ = run_showing("make", "up", keep=lambda line: "Ready" in line)
    ready = (code == 0 and wait_until(lambda: get("/health").status == 200, 60) is not None
             and wait_until_balancer_uses(api_containers()))
    seconds = time.monotonic() - started

    if ready:
        announce_instances()
        get("/orders", show=True)

    return Result("QA-05", "Crear el despliegue completo desde cero",
                  "operativo con las 2 instancias en ≤ 10 min, con un solo comando",
                  f"{seconds:.0f} s con `make up`; operativo: {'sí' if ready else 'no'}",
                  ready and seconds <= 600,
                  ["parte de `make down` (sin contenedores ni volumen); no se borran `.env` ni `api/.venv`"])


def leftovers() -> list[str]:
    containers = run("docker", "ps", "-a", "-q", "--filter", PROJECT_LABEL).split()
    volumes = run("docker", "volume", "ls", "-q", "--filter", PROJECT_LABEL).split()
    networks = run("docker", "network", "ls", "-q", "--filter", PROJECT_LABEL).split()

    return containers + volumes + networks


def documented_cost_factors() -> list[str]:
    """The components of the environment that the cost section of the design does not mention."""
    text = (ROOT.parent / "architecture-design" / "5. local components.md").read_text()
    section = text.split("## 9. Costo")[1].split("\n## ")[0].lower()
    components = {"api y backup": "contenedores", "haproxy": "haproxy", "volumen de datos": "volumen",
                  "imágenes": "imágenes"}

    return [name for name, keyword in components.items() if keyword not in section]


@covers("QA-07")
def tear_down() -> Result:
    live.scenario("QA-07", "Retirar los recursos al terminar las pruebas",
                  "0 recursos activos en ≤ 15 min; factores de consumo identificados para el 100 % de los componentes")

    live.say("bajo todo el entorno (make down) y espero a que no quede nada", "⚡", "yellow")
    run("make", "down")
    cleared = wait_until(lambda: not leftovers(), 900, 2)
    live.say("no quedan contenedores, redes ni volúmenes del proyecto" if cleared is not None
             else f"quedan recursos: {leftovers()}", "🔎")

    undocumented = documented_cost_factors()
    live.say(f"componentes sin factor de consumo documentado: {undocumented or 'ninguno'}", "🔎")

    live.say("dejo el entorno levantado otra vez", "♻️")
    run_showing("make", "up", keep=lambda line: "Ready" in line)

    return Result("QA-07", "Retirar los recursos al terminar las pruebas",
                  "0 recursos activos en ≤ 15 min; factores de consumo identificados para el 100 % de los componentes",
                  f"sin recursos en {seconds_text(cleared)}; componentes sin factor documentado: {undocumented or 'ninguno'}",
                  cleared is not None and cleared <= 900 and not undocumented,
                  ["gasto total: 0, todo corre en la máquina local y no se usa ninguna cuenta de nube",
                   "el entorno se vuelve a levantar al terminar"])


CHECKS = [instance_failure, data_loss, recreated_container, defective_version, clean_start, tear_down]
