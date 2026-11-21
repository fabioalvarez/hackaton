import argparse, datetime, json, os, subprocess, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ["docker", "compose", "-f", str(ROOT / "local" / "compose.yaml")]
ENV_FILE = ROOT / "local" / ".env"
RED = "nodo-ruta_default"
REPO = "nodo-ruta"
SERVICIOS = ["app1", "app2"]   # 2 tareas
INTERVALO = 5                  # s entre health checks (ALB)
UMBRAL_FALLOS = 2              # fallos seguidos -> no sana
UMBRAL_EXITOS = 2              # éxitos seguidos -> sana
GRACIA = 5                     # s de arranque sin evaluar
ESPERA_MAX = 300               # PR-05: rollback en <= 5 min
CONSERVAR = 5                  # imágenes conservadas (ciclo de vida de ECR)


def run(*args, check=True, env=None):
    return subprocess.run(list(args), check=check, capture_output=True, text=True, env=env)


def version_activa():
    if ENV_FILE.exists():
        for linea in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if linea.startswith("VERSION="):
                return linea.split("=", 1)[1].strip()
    return "v1"


def compose(*args, version=None, check=True):
    env = {**os.environ, "VERSION": version or version_activa()}
    return run(*COMPOSE, *args, check=check, env=env)


def sana(contenedor):
    probe = "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)"
    return run("docker", "exec", contenedor, "python", "-c", probe, check=False).returncode == 0


def esperar_healthy(servicio, limite=60):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        cid = compose("ps", "-q", servicio).stdout.strip()
        if cid and run("docker", "inspect", "-f", "{{.State.Health.Status}}", cid, check=False).stdout.strip() == "healthy":
            return True
        time.sleep(1)
    return False


def podar_imagenes(activa):
    tags = [t for t in run("docker", "images", REPO, "--format", "{{.Tag}}").stdout.split() if t != "<none>"]
    for tag in tags[CONSERVAR:]:
        if tag != activa:
            run("docker", "rmi", f"{REPO}:{tag}", check=False)


def construir(version, falla):
    args = ["docker", "build", "-t", f"{REPO}:{version}"]
    if falla:
        args += ["--build-arg", "SIMULAR_FALLA=1"]
    subprocess.run([*args, str(ROOT)], check=True)
    print(f"Imagen {REPO}:{version} lista{' (defectuosa)' if falla else ''}")


def iniciar():
    if not (ROOT / "data" / "pedidos.json").is_file():
        raise SystemExit("Ejecute primero: python scripts/datos.py preparar")
    version = version_activa()
    subprocess.run([*COMPOSE, "up", "-d", "--wait"], check=True, env={**os.environ, "VERSION": version})
    ENV_FILE.write_text(f"VERSION={version}\n", encoding="utf-8")
    print(f"Servicio activo en http://127.0.0.1:8080 con la versión {version}")


def desplegar(version):
    eventos, inicio = [], time.monotonic()

    def log(msg):
        eventos.append({"t_s": round(time.monotonic() - inicio, 1), "evento": msg})
        print(f"[{eventos[-1]['t_s']:>6}s] {msg}", flush=True)

    if run("docker", "image", "inspect", f"{REPO}:{version}", check=False).returncode != 0:
        raise SystemExit(f"No existe {REPO}:{version}. Ejecute: python scripts/desplegar.py construir {version}")
    anterior = version_activa()
    log(f"Despliegue {version}; activa {anterior} en {', '.join(SERVICIOS)}")

    sufijo = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    candidatas = [f"{REPO}-candidata-{i}-{sufijo}" for i in range(1, len(SERVICIOS) + 1)]
    for c in candidatas:
        run("docker", "run", "-d", "--name", c, "--network", RED,
            "-e", f"INSTANCE_ID={c}", "-e", "DATA_PATH=/data/pedidos.json",
            "-v", f"{ROOT / 'data'}:/data:ro", f"{REPO}:{version}")
    log(f"Candidatas lanzadas junto a las activas (máximo 200 %, mínimo 100 %)")

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

    if resultado == "ROLLBACK":
        for c in candidatas:
            log(f"Logs de {c}: {run('docker', 'logs', '--tail', '3', c, check=False).stdout.strip()}")
    for c in candidatas:
        run("docker", "rm", "-f", c, check=False)

    if resultado == "COMPLETADO":
        log("Candidatas sanas; se reemplazan las instancias una a una")
        for s in SERVICIOS:
            compose("up", "-d", "--no-deps", s, version=version)
            if not esperar_healthy(s):
                log(f"{s} no quedó sana con {version}; se vuelve a {anterior}")
                for t in SERVICIOS:
                    compose("up", "-d", "--no-deps", t, version=anterior)
                resultado = "ROLLBACK"
                break
            log(f"{s} actualizada a {version}")
    if resultado == "COMPLETADO":
        ENV_FILE.write_text(f"VERSION={version}\n", encoding="utf-8")
        podar_imagenes(version)
        log(f"Despliegue completado. Activa: {version}")
    else:
        log(f"Rollback automático: sigue activa {anterior}, sin retirar sus instancias")

    duracion = round(time.monotonic() - inicio, 1)
    evidencia = ROOT / "evidencias" / f"despliegue-{version}-{sufijo}.json"
    evidencia.parent.mkdir(parents=True, exist_ok=True)
    evidencia.write_text(json.dumps({
        "version_solicitada": version, "version_anterior": anterior, "resultado": resultado,
        "version_activa": version_activa(), "duracion_s": duracion,
        "cumple_pr05_5min": duracion <= ESPERA_MAX, "eventos": eventos,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Evidencia guardada en", evidencia.relative_to(ROOT))
    return 0 if resultado == "COMPLETADO" else 1


def estado():
    print(f"Versión activa: {version_activa()}")
    print(compose("ps", check=False).stdout)


p = argparse.ArgumentParser(description="Despliegue local de Nodo Ruta con versiones fijas y rollback automático.")
sub = p.add_subparsers(dest="cmd", required=True)
c = sub.add_parser("construir", help="Construye nodo-ruta:<version>")
c.add_argument("version")
c.add_argument("--falla", action="store_true", help="Versión defectuosa: /health devuelve 500 (PR-05)")
sub.add_parser("iniciar", help="Levanta proxy + app1 + app2 con la versión activa")
d = sub.add_parser("desplegar", help="Despliega nodo-ruta:<version> con rollback automático")
d.add_argument("version")
sub.add_parser("estado", help="Versión activa y estado de los contenedores")
a = p.parse_args()
if a.cmd == "construir":
    construir(a.version, a.falla)
elif a.cmd == "iniciar":
    iniciar()
elif a.cmd == "desplegar":
    raise SystemExit(desplegar(a.version))
else:
    estado()
