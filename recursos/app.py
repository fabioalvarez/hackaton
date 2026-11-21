import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DATA = Path(os.environ.get("DATA_PATH", "pedidos.json"))


def instance_id():
    if os.environ.get("INSTANCE_ID"):
        return os.environ["INSTANCE_ID"]
    metadata = os.environ.get("ECS_CONTAINER_METADATA_URI_V4")
    if metadata:
        try:
            import urllib.request
            with urllib.request.urlopen(f"{metadata}/task", timeout=2) as r:
                return "tarea-" + json.loads(r.read())["TaskARN"].rsplit("/", 1)[-1][:8]
        except (OSError, ValueError, KeyError):
            pass
    return "instancia-ejemplo"


INSTANCE = instance_id()
FALLA = os.environ.get("SIMULAR_FALLA") == "1"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = self.path.split("?", 1)[0]
        if route not in ("/", "/health", "/pedidos"):
            status, response = 404, {"error": "Ruta no disponible", "instancia": INSTANCE}
        else:
            try:
                data = json.loads(DATA.read_text(encoding="utf-8"))
                if not isinstance(data.get("pedidos"), list):
                    raise ValueError("Formato de datos inválido")
                status = 200
                if route == "/pedidos":
                    response = {"instancia": INSTANCE, **data}
                elif route == "/health":
                    if FALLA:
                        status, response = 500, {"estado": "falla_simulada", "instancia": INSTANCE}
                    else:
                        response = {"estado": "ok", "instancia": INSTANCE, "version_datos": data.get("version")}
                else:
                    response = {"servicio": "Nodo Ruta - caso ficticio", "instancia": INSTANCE, "rutas": ["/health", "/pedidos"]}
            except (OSError, ValueError, TypeError, AttributeError):
                status, response = 503, {"estado": "error_datos", "instancia": INSTANCE}
        payload = json.dumps(response, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"Nodo Ruta: {INSTANCE}, puerto {port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
