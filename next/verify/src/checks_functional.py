"""Functional requirements (RF-01 to RF-05), checked through the balancer."""

import json

from result import Result, covers
import live
from system import api_containers, get, short, volume_file


@covers("RF-01")
def rf01() -> Result:
    live.say("RF-01: consulto la lista de pedidos", "▶")
    body = get("/orders", show=True).body or {}
    count = len(body.get("orders", []))

    return Result("RF-01", "Consultar pedidos", "los 6 pedidos cargados", f"{count} pedidos", count == 6)


@covers("RF-02")
def rf02() -> Result:
    live.say("RF-02: comparo la versión que muestra la API con la de los datos cargados", "▶")
    shown = (get("/orders", show=True).body or {}).get("data_version")
    loaded = json.loads(volume_file() or "{}").get("data_version")

    return Result("RF-02", "La consulta incluye la versión de los datos", "la versión de los datos cargados",
                  f"respuesta: {shown}, cargada: {loaded}", bool(shown) and shown == loaded)


@covers("RF-03")
def rf03() -> Result:
    live.say("RF-03: abro la página de inicio", "▶")
    response = get("/", show=True)
    ok = response.status == 200 and "service" in (response.body or {})

    return Result("RF-03", "Página de inicio", "200 con el nombre del servicio", f"{response.status}, {response.body}", ok)


@covers("RF-04")
def rf04() -> Result:
    live.say("RF-04: consulto la salud del servicio", "▶")
    response = get("/health", show=True)
    ok = response.status == 200 and (response.body or {}).get("status") == "ok"

    return Result("RF-04", "Salud del servicio", "200 y estado ok", f"{response.status}, {response.body}", ok)


@covers("RF-05")
def rf05() -> Result:
    live.say("RF-05: envío 30 consultas y miro qué instancia responde cada una", "▶")
    responses = [get(path) for path in ["/", "/health", "/orders"] * 10]
    ids = {r.instance for r in responses}
    known = {short(c) for c in api_containers()}
    traceable = all(r.instance in known for r in responses)
    live.say(", ".join(f"{live.names.get(i, i)} ×{sum(r.instance == i for r in responses)}" for i in sorted(ids)), "🔎")

    return Result("RF-05", "Cada respuesta indica la instancia que la atendió",
                  "ID en el 100 % de las respuestas, y las 2 instancias aparecen",
                  f"{len(ids)} instancias distintas en {len(responses)} respuestas",
                  traceable and len(ids) >= 2,
                  [f"instancias vistas: {sorted(ids)}"])


CHECKS = [rf01, rf02, rf03, rf04, rf05]
