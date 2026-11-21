"""Nodo Ruta — API de consulta de entregas.

Servicio único, sin estado, replicable en varias instancias detrás de un punto
de entrada común. Cada instancia lee el mismo archivo de datos desde el
almacenamiento compartido y lo sirve por HTTP.

Mapa de requisitos:
  GET /         -> página de inicio                       (RF-03)
  GET /pedidos  -> pedidos + identificador de versión     (RF-01, RF-02)
  GET /health   -> estado de salud                        (RF-04, QA-01, QA-04)
  X-Instance-Id -> instancia que atendió (todas)          (RF-05, A4)
  log por req.  -> una línea con el ID de instancia       (A6, QA-06)
"""
import json
import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .config import settings

# --- Logging con el ID de instancia en cada línea (A6, QA-06) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s level=%(levelname)s instance=" + settings.instance_id + " %(message)s",
)
logger = logging.getLogger("nodo-ruta")

app = FastAPI(title="Nodo Ruta API", version=settings.app_version)


def leer_datos() -> dict:
    """Lee el archivo de datos en CADA solicitud.

    El servicio no guarda estado propio (A5): así sobrevive a la recreación de
    la instancia (QA-03) y las dos instancias sirven siempre la misma fuente
    compartida (QA-01, P3).
    """
    ruta = Path(settings.data_file)
    with ruta.open(encoding="utf-8") as f:
        return json.load(f)


@app.middleware("http")
async def instancia_y_registro(request: Request, call_next):
    """Agrega X-Instance-Id a toda respuesta y registra la solicitud."""
    inicio = time.perf_counter()
    response = await call_next(request)

    # Identificar la instancia que atendió (RF-05, A4).
    response.headers["X-Instance-Id"] = settings.instance_id

    # Una línea de log por solicitud, trazable a una instancia (A6, QA-06).
    dur_ms = (time.perf_counter() - inicio) * 1000
    logger.info(
        "method=%s path=%s status=%s dur_ms=%.1f",
        request.method,
        request.url.path,
        response.status_code,
        dur_ms,
    )
    return response


@app.get("/", response_class=HTMLResponse)
def inicio() -> str:
    """Página de inicio: confirma que es el servicio correcto (RF-03)."""
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nodo Ruta</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 640px; margin: 3rem auto;
           padding: 0 1rem; line-height: 1.5; }}
    code {{ background: #f0f0f0; padding: .1rem .35rem; border-radius: 4px; }}
    .tag {{ color: #555; font-size: .9rem; }}
  </style>
</head>
<body>
  <h1>🚚 Nodo Ruta</h1>
  <p>Servicio de consulta de entregas. Estás en el servicio correcto.</p>
  <p class="tag">Instancia: <code>{settings.instance_id}</code> ·
     Versión: <code>{settings.app_version}</code></p>
  <ul>
    <li><a href="/pedidos"><code>GET /pedidos</code></a> — pedidos y versión de datos</li>
    <li><a href="/health"><code>GET /health</code></a> — estado del servicio</li>
  </ul>
</body>
</html>"""


@app.get("/pedidos")
def pedidos():
    """Devuelve los pedidos con el identificador de versión (RF-01, RF-02)."""
    datos = leer_datos()
    lista = datos.get("pedidos", [])
    return {
        "version": datos.get("version"),  # RF-02
        "count": len(lista),
        "pedidos": lista,                  # RF-01
    }


@app.get("/health")
def health():
    """Estado de salud (RF-04).

    Si FAIL_HEALTH está activo, simula una versión defectuosa devolviendo 503
    para que el despliegue vuelva solo a la versión anterior (A9, QA-04, PR-05).
    """
    if settings.fail_health:
        logger.warning("health=fail (FAIL_HEALTH activo, simulando versión defectuosa)")
        return JSONResponse(status_code=503, content={"status": "fail"})
    return {"status": "ok"}
