# Nodo Ruta — API

Servicio de consulta de entregas para el reto **Nodo Ruta**. Un servicio único,
sin estado, replicable en varias instancias detrás de un punto de entrada común,
que lee los datos (pedidos + versión) desde un almacenamiento compartido de solo
lectura.

Implementa el contrato definido en el diseño (`architecture-design/`).

## Endpoints

| Método y ruta  | Respuesta                                   | Requisito        |
|----------------|---------------------------------------------|------------------|
| `GET /`        | Página de inicio                            | RF-03            |
| `GET /pedidos` | `{ version, count, pedidos[] }`             | RF-01, RF-02     |
| `GET /health`  | `{ "status": "ok" }` (503 si defectuosa)    | RF-04, QA-01/04  |
| *(todas)*      | Header `X-Instance-Id`                       | RF-05            |

Además, cada solicitud deja una línea de log con el ID de instancia (QA-06).

## Configuración (variables de entorno)

Toda la configuración viene de fuera de la imagen (CT-01):

| Variable      | Por defecto          | Para qué                                            |
|---------------|----------------------|-----------------------------------------------------|
| `DATA_FILE`   | `/data/pedidos.json` | Ruta del archivo de datos (EFS en AWS)              |
| `INSTANCE_ID` | *hostname*           | ID de la instancia (ID de la tarea en ECS)         |
| `APP_VERSION` | `v1`                 | Versión de la imagen                                |
| `FAIL_HEALTH` | `false`              | `true` simula una versión defectuosa (PR-05/QA-04) |

## Correr en local

### Opción 1 — Python directo (una sola instancia)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
DATA_FILE=./data/pedidos.json uvicorn app.main:app --reload --port 8000
```

Luego: http://localhost:8000 · http://localhost:8000/docs (OpenAPI)

### Opción 2 — Docker Compose (2 instancias + balanceador, como el diseño)

```bash
docker compose up --build
```

Punto de entrada común: **http://localhost:8080**

```bash
curl -i http://localhost:8080/pedidos    # mira el header X-Instance-Id
```

## Pruebas automáticas

```bash
pip install -r requirements-dev.txt
pytest
```

## Probar los escenarios del reto con Compose

- **PR-01 (funcionamiento normal):** repetir `curl -i http://localhost:8080/pedidos`
  varias veces; el header `X-Instance-Id` alterna entre `instancia-a` e `instancia-b`.
- **PR-02 (detener una instancia, QA-01):**
  `docker compose stop instancia-a` y seguir consultando: el servicio responde
  con `instancia-b` y el balanceador deja de enviarle tráfico a la caída.
- **PR-03 (recrear contenedor, QA-03):** `docker compose up -d --force-recreate instancia-a`;
  `/pedidos` sigue devolviendo los 6 pedidos y la misma versión.
- **PR-05 (versión defectuosa, QA-04):** `FAIL_HEALTH=true docker compose up -d instancia-a`;
  su `/health` devuelve 503 (en AWS esto dispara el rollback del circuit breaker de ECS).

## Estructura

```
nodo-ruta-api/
├── app/
│   ├── main.py          # API (endpoints, header de instancia, logging)
│   └── config.py        # configuración desde variables de entorno
├── data/
│   └── pedidos.json     # 6 pedidos + versión (almacenamiento compartido)
├── tests/
│   └── test_api.py      # pruebas alineadas con PR-01 y PR-05
├── Dockerfile
├── docker-compose.yml   # 2 instancias + balanceador nginx
├── nginx.conf
├── requirements.txt
└── requirements-dev.txt
```

## De local a AWS

| En local (este repo)      | En AWS (diseño)                      |
|---------------------------|--------------------------------------|
| `instancia-a` / `-b`      | 2 tareas de **ECS Fargate**          |
| `balanceador` (nginx)     | **ALB** con health check             |
| Volumen `./data:ro`       | **EFS** montado en solo lectura      |
| `FAIL_HEALTH` → 503       | **Circuit breaker de ECS** (rollback)|
| Logs a stdout             | **CloudWatch Logs**                  |
