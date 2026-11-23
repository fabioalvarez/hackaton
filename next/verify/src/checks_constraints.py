"""Constraints (CT-01, CT-02) and the automated tests as evidence."""

import re
from pathlib import Path

import live
from commands import ROOT, current_tag, make, run, succeeds
from environment import PROJECT_LABEL
from result import Requirement, check
from service import get

CT_01 = Requirement("CT-01", "Sin secretos en la imagen ni en el repositorio", "ninguno encontrado, y `.env` ignorado por git")
CT_02 = Requirement("CT-02", "Exposición mínima hacia el exterior", "solo HAProxy publica un puerto; las instancias no responden directo; sin /docs")
TESTS = Requirement("TESTS", "Tests automáticos (RF, QA-03, QA-04, QA-06, QA-02 y CT)", "todos pasan")

# What a secret looks like: cloud keys, private keys, and passwords or tokens with a value.
SECRET_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['\"]?[A-Za-z0-9/+_\-]{8,}"),
]


# --- CT-01: no secrets ---------------------------------------------------------------

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


@check(CT_01)
def no_secrets():
    image = f"next-api:{current_tag()}"
    live.step(f"CT-01: busco claves, llaves y contraseñas en el repositorio y en la imagen {image}")
    found = secrets_in_repository() + secrets_in_image(image)
    ignored = succeeds("git", "check-ignore", "-q", ".env")

    return CT_01.result(f"{len(found)} hallazgos, `.env` ignorado: {'sí' if ignored else 'no'}",
                        not found and ignored,
                        [f"archivos revisados: {len(repository_files())}, imagen: {image}"] + found)


# --- CT-02: minimal exposure -----------------------------------------------------------

def published_ports() -> dict[str, str]:
    """Container name -> published ports, only for the containers that publish any."""
    listing = run("docker", "ps", "--filter", PROJECT_LABEL, "--format", "{{.Names}}|{{.Ports}}")
    ports = dict(line.split("|", 1) for line in listing.splitlines())

    return {name: p for name, p in ports.items() if "->" in p}


@check(CT_02)
def minimal_exposure():
    live.step("CT-02: reviso qué contenedores publican puertos y pruebo el acceso directo a la API")
    published = published_ports()
    live.found(f"publican puerto: {published}")
    only_the_balancer = bool(published) and all("haproxy" in name for name in published)
    direct = get("/health", base="http://localhost:8080")
    docs = [get(path).status for path in ("/docs", "/redoc", "/openapi.json")]

    return CT_02.result(f"publican puerto: {sorted(published)}; acceso directo a la API: {'responde' if direct.status else 'no responde'}; "
                        f"/docs, /redoc, /openapi.json: {docs}",
                        only_the_balancer and direct.status == 0 and docs == [404, 404, 404],
                        [f"{name}: {ports}" for name, ports in published.items()])


# --- The automated tests ---------------------------------------------------------------

@check(TESTS)
def automated_tests_pass():
    live.step("TESTS: ejecuto `make test`")
    output = run(*make("test"), check=False).splitlines()
    summary = next((line for line in reversed(output) if " passed" in line or " failed" in line), "sin resultado")

    return TESTS.result(summary.strip("= "), " failed" not in summary and " passed" in summary)


CHECKS = [no_secrets, minimal_exposure, automated_tests_pass]
