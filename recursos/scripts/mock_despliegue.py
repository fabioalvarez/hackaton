import argparse, datetime, json, subprocess, time
from pathlib import Path

REPO = "nodo-ruta"
DESEADAS = 2            # tareas deseadas del servicio ECS
INTERVALO = 5           # s entre health checks (ALB)
UMBRAL_FALLOS = 2       # fallos seguidos -> no sana
UMBRAL_EXITOS = 2       # éxitos seguidos -> sana
GRACIA = 5              # s de arranque sin evaluar
ESPERA_MAX = 300        # PR-05: rollback en <= 5 min
CONSERVAR = 5           # imágenes conservadas (ciclo de vida de ECR)
ESTADO = Path("evidencias/mock_estado.json")


def docker(*args, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def sana(nombre):
    probe = "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
    return docker("exec", nombre, "python", "-c", probe, check=False).returncode == 0


def leer_estado():
    return json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"version": None, "tareas": []}


def guardar_estado(estado):
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(estado, indent=2), encoding="utf-8")


def retirar(tareas):
    for t in tareas:
        docker("rm", "-f", t, check=False)


def podar_imagenes(activa):
    tags = [t for t in docker("images", REPO, "--format", "{{.Tag}}").stdout.split() if t != "<none>"]
    for tag in tags[CONSERVAR:]:
        if tag != activa:
            docker("rmi", f"{REPO}:{tag}", check=False)


def desplegar(version):
    eventos, inicio = [], time.monotonic()

    def log(msg):
        eventos.append({"t_s": round(time.monotonic() - inicio, 1), "evento": msg})
        print(f"[{eventos[-1]['t_s']:>6}s] {msg}", flush=True)

    if docker("image", "inspect", f"{REPO}:{version}", check=False).returncode != 0:
        raise SystemExit(f"No existe la imagen {REPO}:{version}. Constrúyanla primero con docker build.")

    estado = leer_estado()
    anterior = estado["version"]
    log(f"Despliegue {version}; activa: {anterior or 'ninguna'} con {len(estado['tareas'])} tareas")

    sufijo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    candidatas = [f"{REPO}-{version}-{i}-{sufijo}" for i in range(1, DESEADAS + 1)]
    for c in candidatas:
        docker("run", "-d", "--name", c, "-e", f"INSTANCE_ID={c}", f"{REPO}:{version}")
    log(f"Lanzadas {DESEADAS} candidatas (máximo 200 %): {', '.join(candidatas)}")

    time.sleep(GRACIA)
    fallos = {c: 0 for c in candidatas}
    exitos = {c: 0 for c in candidatas}
    resultado = None
    while resultado is None:
        for c in candidatas:
            if sana(c):
                exitos[c], fallos[c] = exitos[c] + 1, 0
            else:
                fallos[c], exitos[c] = fallos[c] + 1, 0
                log(f"{c}: health check fallido ({fallos[c]}/{UMBRAL_FALLOS})")
        if any(f >= UMBRAL_FALLOS for f in fallos.values()):
            resultado = "ROLLBACK"
        elif all(e >= UMBRAL_EXITOS for e in exitos.values()):
            resultado = "COMPLETADO"
        elif time.monotonic() - inicio > ESPERA_MAX:
            resultado = "ROLLBACK"
            log("Tiempo máximo superado")
        else:
            time.sleep(INTERVALO)

    if resultado == "COMPLETADO":
        retirar(estado["tareas"])
        guardar_estado({"version": version, "tareas": candidatas})
        podar_imagenes(version)
        log(f"Candidatas sanas; retiradas las tareas de {anterior or 'ninguna'}. Activa: {version}")
    else:
        for c in candidatas:
            log(f"Logs de {c}: {docker('logs', '--tail', '3', c, check=False).stdout.strip()}")
        retirar(candidatas)
        log(f"Circuit breaker: rollback. Sigue activa {anterior or 'ninguna'} sin interrupción (mínimo 100 %)")

    duracion = round(time.monotonic() - inicio, 1)
    evidencia = Path(f"evidencias/despliegue-{version}-{sufijo}.json")
    evidencia.parent.mkdir(parents=True, exist_ok=True)
    evidencia.write_text(json.dumps({
        "version_solicitada": version, "version_anterior": anterior, "resultado": resultado,
        "version_activa": leer_estado()["version"], "duracion_s": duracion,
        "cumple_pr05_5min": duracion <= ESPERA_MAX, "eventos": eventos,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Evidencia guardada en", evidencia)
    return 0 if resultado == "COMPLETADO" else 1


def mostrar_estado():
    estado = leer_estado()
    print(json.dumps(estado, indent=2))
    for t in estado["tareas"]:
        print(t, "sana" if sana(t) else "NO sana")


def destruir():
    retirar(leer_estado()["tareas"])
    ESTADO.unlink(missing_ok=True)
    print("Tareas del mock retiradas")


p = argparse.ArgumentParser(description="Mock local del despliegue ECS con circuit breaker (PR-05). No sustituye la prueba en AWS.")
sub = p.add_subparsers(dest="cmd", required=True)
d = sub.add_parser("desplegar", help="Despliega nodo-ruta:<version> con rollback automático")
d.add_argument("version")
sub.add_parser("estado", help="Muestra la versión activa y la salud de sus tareas")
sub.add_parser("destruir", help="Retira las tareas del mock")
a = p.parse_args()
if a.cmd == "desplegar":
    raise SystemExit(desplegar(a.version))
if a.cmd == "estado":
    mostrar_estado()
if a.cmd == "destruir":
    destruir()
