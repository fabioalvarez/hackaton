"""Functional requirements (RF-01 to RF-05), checked through the balancer."""

import json

import live
from environment import api_containers, short, volume_file
from result import Requirement, check
from service import get

RF_01 = Requirement("RF-01", "Consultar pedidos", "los 6 pedidos cargados")
RF_02 = Requirement("RF-02", "La respuesta incluye la versión de los datos", "la versión de los datos cargados, en el header X-Data-Version")
RF_03 = Requirement("RF-03", "Página de inicio", "200 con una página HTML que enlaza a las otras páginas")
RF_04 = Requirement("RF-04", "Salud del servicio", "200 y estado ok")
RF_05 = Requirement("RF-05", "Cada respuesta indica la instancia que la atendió", "ID en el 100 % de las respuestas, y las 2 instancias aparecen")


@check(RF_01)
def orders_are_listed():
    live.step("RF-01: consulto la lista de pedidos")
    count = len((get("/orders", show=True).body or {}).get("orders", []))

    return RF_01.result(f"{count} pedidos", count == 6)


@check(RF_02)
def version_is_in_the_header():
    live.step("RF-02: comparo la versión que informa la API (header X-Data-Version) con la de los datos cargados")
    shown = get("/orders", show=True).version
    loaded = json.loads(volume_file() or "{}").get("data_version")

    return RF_02.result(f"respuesta: {shown}, cargada: {loaded}", bool(shown) and shown == loaded)


@check(RF_03)
def home_page_links_to_the_others():
    live.step("RF-03: abro la página de inicio")
    response = get("/", show=True)
    is_html = "text/html" in response.headers.get("content-type", "") and "<html" in response.text
    links = [path for path in ("/orders", "/health") if f'href="{path}"' in response.text]

    return RF_03.result(f"{response.status}, {response.headers.get('content-type')}, enlaces: {', '.join(links) or 'ninguno'}",
                        response.status == 200 and is_html and len(links) == 2)


@check(RF_04)
def health_is_ok():
    live.step("RF-04: consulto la salud del servicio")
    response = get("/health", show=True)
    ok = response.status == 200 and (response.body or {}).get("status") == "ok"

    return RF_04.result(f"{response.status}, {response.body}", ok)


@check(RF_05)
def every_response_names_its_instance():
    live.step("RF-05: envío 30 consultas y miro qué instancia responde cada una")
    responses = [get(path) for path in ["/", "/health", "/orders"] * 10]
    instances = {r.instance for r in responses}
    known = {short(c) for c in api_containers()}
    live.found(", ".join(f"{live.names.get(i, i)} ×{sum(r.instance == i for r in responses)}" for i in sorted(instances)))

    return RF_05.result(f"{len(instances)} instancias distintas en {len(responses)} respuestas",
                        all(r.instance in known for r in responses) and len(instances) >= 2,
                        [f"instancias vistas: {sorted(instances)}"])


CHECKS = [orders_are_listed, version_is_in_the_header, home_page_links_to_the_others, health_is_ok, every_response_names_its_instance]
