"""Checks the requirements and quality scenarios against the running environment, showing what
happens as it happens, and keeps the evidence in `validations/verification.md`.

    make verify                     all of them
    make verify ONLY=QA-01,RF-02    only those (the report is not updated)
    make verify STEP=1              waits for Enter before each scenario that changes the environment
    make verify YES=1               does not ask before the scenarios that change the environment

Where things are:
    checks_functional.py   RF-01 to RF-05
    checks_constraints.py  CT-01, CT-02 and the automated tests
    checks_quality.py      QA-01 to QA-07
    commands.py, service.py, environment.py   what the checks use: commands, the service, containers and data
    live.py, watching.py   what is printed while they run
    result.py, report.py   what a check reports, and the report
"""

import argparse
import sys
from contextlib import nullcontext

import checks_constraints
import checks_functional
import checks_quality
import live
from commands import ROOT
from environment import announce_instances
from report import print_summary, sort_key, write_markdown
from result import Result
from service import get
from watching import Watching

REPORT = ROOT.parent / "validations" / "verification.md"
ALL_CHECKS = checks_functional.CHECKS + checks_constraints.CHECKS + checks_quality.CHECKS
GROUPS = {"functional": "Requisitos funcionales", "non-functional": "Requisitos no funcionales (atributos de calidad y constraints)"}


def read_options() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", help="IDs separated by commas, for example QA-01,RF-02")
    parser.add_argument("--yes", action="store_true", help="do not ask before the scenarios that change the environment")
    parser.add_argument("--step", action="store_true", help="wait for Enter before each scenario that changes the environment")

    return parser.parse_args()


def choose(only: str | None) -> list:
    if not only:
        return ALL_CHECKS

    wanted = {id.strip().upper() for id in only.split(",")}

    return [check for check in ALL_CHECKS if wanted & set(check.ids)]


def confirmed(checks: list, yes: bool) -> bool:
    """The scenarios that change the environment ask first, unless told not to."""
    risky = [check for check in checks if check.changes_environment]

    if yes or not risky:
        return True

    print("Estas comprobaciones cambian el entorno: matan y recrean contenedores, rompen los datos,")
    print("despliegan versiones y lo bajan y levantan por completo.")
    print("Al terminar el entorno queda levantado. El volumen de datos vuelve a los datos iniciales")
    print("(store/data/orders.json): lo que hayas cargado con `make load-data` se pierde.")
    print("Los respaldos de store/backups no se borran.")
    print("Se ejecutarán:", ", ".join(id for check in risky for id in check.ids))

    return sys.stdin.isatty() and input("¿Continuar? [s/N] ").strip().lower() == "s"


def group_of(check) -> str:
    return "functional" if check.ids[0].startswith("RF") else "non-functional"


def attempt(check) -> list[Result]:
    """Runs a check. One that breaks is reported as failed, so it does not hide the others."""
    try:
        outcome = check()
    except Exception as error:
        return [requirement.result(f"error: {error}", passed=False) for requirement in check.requirements]

    return outcome if isinstance(outcome, list) else [outcome]


def run_check(check, step: bool) -> list[Result]:
    if step and check.changes_environment:
        live.pause(f"Siguiente: {', '.join(check.ids)}")

    with Watching(ROOT) if check.changes_environment else nullcontext():
        results = attempt(check)

    for result in results:
        live.verdict(result)

    return results


def main() -> None:
    options = read_options()
    checks = choose(options.only)

    if not checks:
        sys.exit("No hay comprobaciones para esos IDs.")

    if any(check.needs_environment for check in checks) and get("/health").status != 200:
        sys.exit("El entorno no está levantado: ejecuta `make up` primero.")

    if not confirmed(checks, options.yes):
        sys.exit("Cancelado. Usa `make verify YES=1` para ejecutar todo sin preguntar.")

    results, group = [], None

    for check in checks:
        if group_of(check) != group:
            group = group_of(check)
            live.heading(GROUPS[group])

            if group == "functional":
                announce_instances()

        results += run_check(check, options.step)

    results.sort(key=sort_key)
    print_summary(results)

    if options.only:
        print("\nEjecución parcial: el informe no se actualiza.")
    else:
        write_markdown(results, REPORT)
        print(f"\nInforme: {REPORT.relative_to(ROOT.parent)}")

    sys.exit(0 if all(r.passed for r in results) else 1)


if __name__ == "__main__":
    main()
