"""Shows the results in the terminal and saves them as a Markdown report."""

from datetime import datetime
from pathlib import Path

from result import Result


def mark(result: Result) -> str:
    return "CUMPLE" if result.passed else "NO CUMPLE"


def print_summary(results: list[Result]) -> None:
    """One line per check: what each one showed live is not repeated."""
    width = max(len(r.id) for r in results) if results else 0
    print("\n━━ Resumen")

    for r in results:
        print(f"   {'✅' if r.passed else '❌'} {r.id:<{width}}  {r.title}")

    passed = sum(r.passed for r in results)
    print(f"\n   {passed} de {len(results)} cumplen.")


def markdown(results: list[Result], generated_at: datetime) -> str:
    passed = sum(r.passed for r in results)
    lines = [
        "# Verificación de requisitos — Nodo Ruta",
        "",
        f"Generado: {generated_at:%Y-%m-%d %H:%M:%S} · **{passed} de {len(results)} cumplen**",
        "",
        "| ID | Qué se comprueba | Esperado | Medido | Resultado |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| {r.id} | {r.title} | {r.expected} | {r.measured} | {mark(r)} |" for r in results]

    for r in results:
        if r.evidence:
            lines += ["", f"## {r.id}", ""] + [f"- {line}" for line in r.evidence]

    return "\n".join(lines) + "\n"


def write_markdown(results: list[Result], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown(results, datetime.now()))
