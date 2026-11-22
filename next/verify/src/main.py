"""Usage: python main.py [--only QA-01,RF-02] [--yes] [--step]

Checks the requirements and quality scenarios against the running environment (`make up`),
showing what happens as it happens, and writes `reports/verification.md`.
--step waits for Enter before each scenario, so the person presenting can explain it.
"""

import sys
from pathlib import Path

import checks_constraints
import checks_functional
import checks_quality
import live
from report import print_summary, write_markdown
from result import Result
from system import ROOT, announce_instances, get

REPORT = ROOT / "reports" / "verification.md"
CHANGES_THE_ENVIRONMENT = {"QA-01", "QA-02", "QA-03", "QA-04", "QA-05", "QA-06", "QA-07"}
BRINGS_IT_UP_ITSELF = {"QA-05", "QA-07"}


def select(checks: list, only: set[str]) -> list:
    return [check for check in checks if not only or only & set(check.ids)]


def run_check(check) -> list[Result]:
    try:
        results = check()
    except Exception as error:  # a check that breaks must not hide the others
        results = [Result(i, "la comprobación falló", "—", f"error: {error}", False) for i in check.ids]

    results = results if isinstance(results, list) else [results]

    for result in results:
        live.verdict(result)

    return results


def confirm(checks: list) -> bool:
    print("Estas comprobaciones cambian el entorno: matan y recrean contenedores, rompen los datos,")
    print("despliegan versiones y lo bajan y levantan por completo.")
    print("Al terminar el entorno queda levantado. El volumen de datos vuelve a los datos iniciales")
    print("(store/data/orders.json): lo que hayas cargado con `make load-data` se pierde.")
    print("Los respaldos de store/backups no se borran.")
    print("Se ejecutarán:", ", ".join(i for c in checks for i in c.ids))

    return sys.stdin.isatty() and input("¿Continuar? [s/N] ").strip().lower() == "s"


def main() -> None:
    arguments = sys.argv[1:]
    only = set()

    if "--only" in arguments:
        only = {i.strip().upper() for i in arguments[arguments.index("--only") + 1].split(",")}

    safe = select(checks_functional.CHECKS + checks_constraints.CHECKS, only)
    risky = select(checks_quality.CHECKS, only)
    needed = {i for c in safe + risky for i in c.ids}

    if not needed:
        sys.exit("No hay comprobaciones para esos IDs.")

    if not needed <= BRINGS_IT_UP_ITSELF and get("/health").status != 200:
        sys.exit("El entorno no está levantado: ejecuta `make up` primero.")

    if risky and "--yes" not in arguments and not confirm(risky):
        sys.exit("Cancelado. Usa `make verify YES=1` para ejecutar todo sin preguntar.")

    step = "--step" in arguments
    results = []

    functional = [check for check in safe if check.ids[0].startswith("RF")]
    non_functional = [check for check in safe if check not in functional]

    if functional:
        live.heading("Requisitos funcionales")
        if get("/health").status == 200:
            announce_instances()

        for check in functional:
            results += run_check(check)

    if non_functional or risky:
        live.heading("Requisitos no funcionales (atributos de calidad y constraints)")

    for check in non_functional:
        results += run_check(check)

    for check in risky:
        if step:
            live.pause(f"Siguiente: {', '.join(check.ids)}")

        with live.Watching(ROOT):
            results += run_check(check)

    results.sort(key=lambda r: (r.id[:2] == "QA", r.id[:2] == "CT", r.id))
    print_summary(results)
    write_markdown(results, REPORT)
    print(f"Informe: {REPORT.relative_to(ROOT)}")

    sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
