"""The summary shown at the end, and the Markdown report that is kept as evidence."""

from datetime import datetime
from pathlib import Path

from result import Result

ORDER = {"RF": 0, "CT": 1, "TE": 2, "QA": 3}   # functional, constraints, automated tests, quality scenarios


def sort_key(result: Result) -> tuple:
    return (ORDER[result.id[:2]], result.id)


def print_summary(results: list[Result]) -> None:
    """One line per check: what each one showed while it ran is not repeated."""
    width = max(len(r.id) for r in results)
    print("\n━━ Resumen")

    for r in results:
        print(f"   {'✅' if r.passed else '❌'} {r.id:<{width}}  {r.title}")

    print(f"\n   {sum(r.passed for r in results)} de {len(results)} cumplen.")


def markdown(results: list[Result], generated_at: datetime) -> str:
    lines = [
        "# Verificación de requisitos — Nodo Ruta",
        "",
        f"Generado: {generated_at:%Y-%m-%d %H:%M:%S} · **{sum(r.passed for r in results)} de {len(results)} cumplen**",
        "",
        "| ID | Qué se comprueba | Esperado | Medido | Resultado |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {r.id} | {r.title} | {r.expected} | {r.measured} | {'CUMPLE' if r.passed else 'NO CUMPLE'} |" for r in results]

    for r in results:
        if r.evidence:
            lines += ["", f"## {r.id}", ""] + [f"- {line}" for line in r.evidence]

    return "\n".join(lines) + "\n"


def write_markdown(results: list[Result], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown(results, datetime.now()))
