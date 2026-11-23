"""Quality scenarios (QA-01 to QA-07).

Every scenario has the same shape:
    1. start from a working service,
    2. cause the stimulus, telling what is done,
    3. measure the response,
    4. report it against the criterion of the design.

They change the environment (kill and recreate containers, break the data, deploy versions, take
everything down) and leave it running at the end.
"""

import hashlib
import json
import time
from pathlib import Path

import live
from commands import ROOT, current_tag, make, next_version, run, run_showing
from environment import (announce_instances, api_containers, corrupt_data, delete_data, name_of, project_resources,
                         restore_replicas, seconds_until_haproxy_removed, short, start_from_a_working_service,
                         volume_file, volume_hash, wait_until_balancer_uses, haproxy_down_events)
from result import Requirement, check
from service import Traffic, get, success_rate, wait_until

QA_01 = Requirement("QA-01", "Una instancia se detiene con consultas en curso", "≥ 99 % de solicitudes exitosas; HAProxy deja de enviarle solicitudes en ≤ 10 s")
QA_02 = Requirement("QA-02", "Los datos se pierden", "restaurados sin intervención en ≤ 5 min; versión y contenido idénticos al respaldo")
QA_03 = Requirement("QA-03", "Se recrea un contenedor del servicio", "0 pedidos perdidos o modificados; misma versión antes y después")
QA_04 = Requirement("QA-04", "Se publica una versión que no funciona", "servicio restablecido en ≤ 5 min con la versión anterior; 0 pedidos perdidos")
QA_05 = Requirement("QA-05", "Crear el despliegue completo desde cero", "operativo con las 2 instancias en ≤ 10 min, con un solo comando")
QA_06 = Requirement("QA-06", "Diagnosticar el incidente con los logs", "instancia afectada identificada en ≤ 120 s; 100 % de las solicitudes asociadas a una instancia")
QA_07 = Requirement("QA-07", "Retirar los recursos al terminar las pruebas", "0 recursos activos en ≤ 15 min; factores de consumo identificados para el 100 % de los componentes")


def begin(*requirements: Requirement) -> None:
    """The start of a scenario: says what it checks, and makes sure the service works."""
    live.scenario(requirements)
    start_from_a_working_service()


def seconds_text(seconds: float | None) -> str:
    return "no ocurrió" if seconds is None else f"{seconds:.1f} s"


# --- QA-01 and QA-06: an instance fails ---------------------------------------------

@check(QA_01, QA_06, changes_environment=True)
def an_instance_fails():
    begin(QA_01, QA_06)
    victim = api_containers()[0]
    known = {short(c) for c in api_containers()}

    with Traffic() as traffic:
        live.step("empiezo a enviar una consulta cada 0,25 s a través del balanceador")
        time.sleep(3)

        live.stimulus(f"detengo la instancia {name_of(victim)} de golpe (docker kill)")
        killed_at = time.time()
        run("docker", "kill", victim)
        wait_until(lambda: haproxy_down_events(killed_at - 1), 60)      # until HAProxy notices
        time.sleep(5)

    live.restoring("levanto de nuevo la réplica para dejar el entorno completo")
    restore_replicas()

    removed_after = seconds_until_haproxy_removed(killed_at)
    rate = success_rate(traffic.responses)
    answered = [r for r in traffic.responses if r.status == 200]
    unknown = [r for r in answered if r.instance not in known]

    return [
        QA_01.result(f"{rate:.1%} de {len(traffic.responses)} solicitudes; HAProxy la sacó en {seconds_text(removed_after)}",
                     rate >= 0.99 and removed_after is not None and removed_after <= 10,
                     [f"instancia detenida: {name_of(victim)}"]),
        QA_06.result(f"identificada en {seconds_text(removed_after)} (log de HAProxy: `Server api/... DOWN`); "
                     f"{len(answered) - len(unknown)} de {len(answered)} solicitudes con instancia conocida",
                     removed_after is not None and removed_after <= 120 and not unknown,
                     ["comandos de diagnóstico: `docker compose ps -a` y `docker compose logs haproxy`"]),
    ]


# --- QA-02: the data is lost ---------------------------------------------------------

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@check(QA_02, changes_environment=True)
def the_data_is_lost():
    begin(QA_02)
    original = volume_hash()
    version = json.loads(volume_file())["data_version"]
    backup = ROOT / "store" / "backups" / f"orders-{version}.json"

    live.found(f"el vigilante tiene un respaldo de la versión {version}; compruebo que es igual a los datos")
    backed_up = wait_until(lambda: backup.exists() and sha256(backup) == original, 30)

    recovered_in = {}
    with Traffic():
        live.step("sigo consultando la API mientras se pierden los datos")
        time.sleep(2)

        for cause, lose in (("archivo inválido", corrupt_data), ("archivo borrado", delete_data)):
            live.stimulus(f"dejo los datos así: {cause}")
            lose()
            recovered_in[cause] = wait_until(lambda: volume_hash() == original, 300)
            live.say(f"los datos volvieron a ser idénticos al respaldo ({seconds_text(recovered_in[cause])})", "💾")
            time.sleep(3)

    start_from_a_working_service()
    restored = all(seconds is not None and seconds <= 300 for seconds in recovered_in.values())

    return QA_02.result("; ".join(f"{cause}: {seconds_text(s)}" for cause, s in recovered_in.items())
                        + f"; coincide con el respaldo de {version}: {'sí' if backed_up is not None else 'no'}",
                        backed_up is not None and restored,
                        [f"hash del respaldo = hash restaurado = {original[:16]}..."])


# --- QA-03: a container is recreated -------------------------------------------------

@check(QA_03, changes_environment=True)
def a_container_is_recreated():
    begin(QA_03)

    live.step("consulto los pedidos antes de tocar nada")
    before = get("/orders", show=True)

    victim = api_containers()[0]
    with Traffic():
        live.stimulus(f"elimino el contenedor {name_of(victim)} y dejo que se cree otro")
        run("docker", "rm", "-f", victim)
        restore_replicas()

    live.step("consulto los pedidos otra vez")
    announce_instances()
    after = get("/orders", show=True)

    lost = len((before.body or {}).get("orders", [])) - len((after.body or {}).get("orders", []))
    same = before.body == after.body and before.version == after.version

    return QA_03.result(f"{lost} pedidos perdidos; versión {before.version} → {after.version}; contenido {'igual' if same else 'distinto'}",
                        same and lost == 0)


# --- QA-04: a defective version is deployed ------------------------------------------

def deploy(tag: str, broken: bool = False) -> tuple[int, str]:
    """`make deploy`, with its steps shown as they happen. Returns the exit code and the output."""
    return run_showing("python3", "deploy/src/main.py", tag, *(["--break"] if broken else []))


@check(QA_04, changes_environment=True)
def a_defective_version_is_deployed():
    begin(QA_04)

    good = next_version()
    live.deploying(f"primero despliego una versión buena ({good})")
    good_code, _ = deploy(good)
    announce_instances()
    before = get("/orders", show=True)

    live.deploying("ahora despliego una versión defectuosa, que no arranca, con consultas en curso", "yellow")
    with Traffic() as traffic:
        time.sleep(3)
        started = time.monotonic()
        broken_code, output = deploy("broken", broken=True)
        seconds = time.monotonic() - started
        time.sleep(5)

    live.found("compruebo que sigue corriendo la versión buena y que los datos no cambiaron")
    after = get("/orders", show=True)
    same_data = before.body == after.body and before.version == after.version
    images = {run("docker", "inspect", "-f", "{{.Config.Image}}", c) for c in api_containers()}
    failed = sum(r.status != 200 for r in traffic.responses)
    good_version_stays = images == {f"next-api:{good}"} and current_tag() == good

    return QA_04.result(f"descartada en {seconds:.0f} s (salida {broken_code}); versión vigente {current_tag()}; "
                        f"{failed} solicitudes fallidas de {len(traffic.responses)}; datos {'iguales' if same_data else 'distintos'}",
                        good_code == 0 and broken_code == 1 and seconds <= 300 and good_version_stays and failed == 0 and same_data,
                        [f"despliegue bueno {good}: salida {good_code}", output.strip().splitlines()[-1]])


# --- QA-05: everything from scratch --------------------------------------------------

@check(QA_05, changes_environment=True, needs_environment=False)
def everything_from_scratch():
    live.scenario((QA_05,))

    live.stimulus("bajo todo el entorno (make down)")
    run(*make("down"))

    live.step("lo levanto con un solo comando (make up)")
    started = time.monotonic()
    code, _ = run_showing(*make("up"), keep=lambda line: "Ready" in line)
    ready = (code == 0 and wait_until(lambda: get("/health").status == 200, 60) is not None
             and wait_until_balancer_uses(api_containers()))
    seconds = time.monotonic() - started

    if ready:
        announce_instances()
        get("/orders", show=True)

    return QA_05.result(f"{seconds:.0f} s con `make up`; operativo: {'sí' if ready else 'no'}",
                        ready and seconds <= 600,
                        ["parte de `make down` (sin contenedores ni volumen); no se borran `.env` ni `api/.venv`"])


# --- QA-07: back to nothing ----------------------------------------------------------

def undocumented_cost_factors() -> list[str]:
    """The components of the environment that the cost section of the design does not mention."""
    text = (ROOT.parent / "architecture-design" / "4. local components.md").read_text()
    section = text.split("## 9. Costo")[1].split("\n## ")[0].lower()
    components = {"api y backup": "contenedores", "haproxy": "haproxy", "volumen de datos": "volumen", "imágenes": "imágenes"}

    return [name for name, keyword in components.items() if keyword not in section]


@check(QA_07, changes_environment=True, needs_environment=False)
def back_to_nothing():
    live.scenario((QA_07,))

    live.stimulus("bajo todo el entorno (make down) y espero a que no quede nada")
    run(*make("down"))
    cleared_in = wait_until(lambda: not project_resources(), 900, 2)
    live.found("no quedan contenedores, redes ni volúmenes del proyecto" if cleared_in is not None
               else f"quedan recursos: {project_resources()}")

    undocumented = undocumented_cost_factors()
    live.found(f"componentes sin factor de consumo documentado: {undocumented or 'ninguno'}")

    live.restoring("dejo el entorno levantado otra vez")
    run_showing(*make("up"), keep=lambda line: "Ready" in line)

    return QA_07.result(f"sin recursos en {seconds_text(cleared_in)}; componentes sin factor documentado: {undocumented or 'ninguno'}",
                        cleared_in is not None and cleared_in <= 900 and not undocumented,
                        ["gasto total: 0, todo corre en la máquina local y no se usa ninguna cuenta de nube",
                         "el entorno se vuelve a levantar al terminar"])


CHECKS = [an_instance_fails, the_data_is_lost, a_container_is_recreated, a_defective_version_is_deployed,
          everything_from_scratch, back_to_nothing]
