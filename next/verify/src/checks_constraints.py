"""Constraints (CT-01, CT-02) and the automated tests as evidence."""

import re
from pathlib import Path

import live
from result import Result, covers
from system import ROOT, current_tag, get, run, succeeds

# What a secret looks like: cloud keys, private keys, and passwords or tokens with a value.
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{8,}"),
]


def find_secrets(text: str) -> list[str]:
    return [m.group(0) for pattern in SECRET_PATTERNS for m in pattern.finditer(text)]


def repository_files() -> list[Path]:
    """Files git tracks or would track: what could end up in the repository."""
    listing = run("git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", ".")

    return [ROOT / name for name in listing.split("\0") if name and (ROOT / name).is_file() and name != "api/uv.lock"]


def secrets_in_repository() -> list[str]:
    found = []

    for path in repository_files():
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue

        found += [f"{path.relative_to(ROOT)}: {secret[:20]}..." for secret in find_secrets(text)]

    return found


def secrets_in_image(image: str) -> list[str]:
    environment = run("docker", "image", "inspect", "-f", "{{json .Config.Env}}", image)
    history = run("docker", "history", "--no-trunc", "--format", "{{.CreatedBy}}", image)
    files = run("docker", "run", "--rm", "--entrypoint", "sh", image, "-c",
                "find /app -name '.env*' -o -name 'orders*.json' 2>/dev/null")

    return [f"imagen: {secret[:20]}..." for secret in find_secrets(environment + history)] + \
           [f"imagen: archivo {name}" for name in files.split()]


@covers("CT-01")
def ct01() -> Result:
    image = f"next-api:{current_tag()}"
    live.say(f"CT-01: busco claves, llaves y contraseñas en el repositorio y en la imagen {image}", "▶")
    found = secrets_in_repository() + secrets_in_image(image)
    ignored = succeeds("git", "check-ignore", "-q", ".env")

    return Result("CT-01", "Sin secretos en la imagen ni en el repositorio",
                  "ninguno encontrado, y `.env` ignorado por git",
                  f"{len(found)} hallazgos, `.env` ignorado: {'sí' if ignored else 'no'}",
                  not found and ignored,
                  [f"archivos revisados: {len(repository_files())}, imagen: {image}"] + found)


def published_ports() -> dict[str, str]:
    """Container name -> published ports, only for the ones that publish any."""
    listing = run("docker", "ps", "--filter", "label=com.docker.compose.project=next", "--format", "{{.Names}}|{{.Ports}}")
    ports = dict(line.split("|", 1) for line in listing.splitlines())

    return {name: p for name, p in ports.items() if "->" in p}


@covers("CT-02")
def ct02() -> Result:
    live.say("CT-02: reviso qué contenedores publican puertos y pruebo el acceso directo a la API", "▶")
    published = published_ports()
    live.say(f"publican puerto: {published}", "🔎")
    only_balancer = list(published) and all("haproxy" in name for name in published)
    direct = get("/health", base="http://localhost:8080")
    docs = [get(path).status for path in ("/docs", "/redoc", "/openapi.json")]
    ok = only_balancer and direct.status == 0 and docs == [404, 404, 404]

    return Result("CT-02", "Exposición mínima hacia el exterior",
                  "solo HAProxy publica un puerto; las instancias no responden directo; sin /docs",
                  f"publican puerto: {sorted(published)}; acceso directo a la API: {'responde' if direct.status else 'no responde'}; /docs, /redoc, /openapi.json: {docs}",
                  bool(ok), [f"{name}: {ports}" for name, ports in published.items()])


@covers("TESTS")
def tests() -> Result:
    live.say("TESTS: ejecuto `make test`", "▶")
    output = run("make", "test", check=False).splitlines()
    summary = next((line for line in reversed(output) if " passed" in line or " failed" in line), "sin resultado")
    passed = " failed" not in summary and " passed" in summary

    return Result("TESTS", "Tests automáticos (RF, QA-03, QA-04, QA-06, QA-02 y CT)", "todos pasan",
                  summary.strip("= "), passed)


CHECKS = [ct01, ct02, tests]
