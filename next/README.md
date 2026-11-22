# Next · API de pedidos (Nodo Ruta)

Servicio de consulta de entregas. Solo lectura: lee los pedidos de un archivo JSON y los expone por HTTP.

## Requisitos

- [uv](https://docs.astral.sh/uv/) (para correr sin Docker)
- Docker (para correr en contenedor)
- `make`

## Comandos

Todos se ejecutan dentro de `next/`. `make help` muestra la lista.

| Comando | Qué hace |
|---|---|
| `make env` | Crea el entorno `api/.venv` (`uv sync`) y el archivo `.env` a partir de `.env.example` si no existe |
| `make up-local` | Levanta **una** instancia de la API **sin Docker** en http://localhost:8080 |
| `make up` | Levanta con Docker **HAProxy y 2 instancias** (`api-1`, `api-2`) en http://localhost:8000. Si Docker está apagado, lo inicia y espera a que esté listo. Carga `api/data/orders.json` en el volumen si está vacío |
| `make down` | Elimina contenedores, red y volumen de datos |
| `make logs` | Sigue los logs de HAProxy y de las 2 instancias |
| `make load-data FILE=ruta` | Reemplaza el archivo de datos del volumen por el indicado |
| `make test` | Ejecuta las pruebas |

Con `make up`, la API solo se alcanza por HAProxy (puerto `8000`); las instancias no publican puerto. El header `X-Instance-Id` indica cuál respondió: `api-1` o `api-2`.

```bash
for i in $(seq 10); do curl -s -o /dev/null -D - localhost:8000/orders | grep -i x-instance-id; done | sort | uniq -c
```

## Endpoints

| Ruta | Respuesta |
|---|---|
| `GET /` | Nombre del servicio y rutas disponibles |
| `GET /health` | `{"status": "ok", "data_version": ...}`; `503` si los datos no se pueden leer |
| `GET /orders` | Los pedidos y la versión de los datos; `503` si los datos no se pueden leer |

Toda respuesta incluye el header `X-Instance-Id` con la instancia que la atendió.

```bash
curl -i http://localhost:8080/orders
```

## Configuración

Variables de entorno (ninguna es un secreto):

| Variable | Por defecto | Uso |
|---|---|---|
| `DATA_PATH` | `/data/orders.json` | Archivo de datos |
| `INSTANCE_ID` | nombre del host | Identificador de la instancia |
| `SERVICE_NAME` | `Next` | Nombre que muestra `GET /` |
| `PORT` | `8080` | Puerto de escucha |
| `LOG_LEVEL` | `info` | Nivel de logs (`debug` muestra también los `/health` correctos) |

Se leen de las variables de entorno y, si no están, del archivo `.env` (copia local de `.env.example`, ignorado por git y fuera del contexto de Docker).

- `make up-local` carga los valores del `.env`.
- `make up` pasa el `.env` a las instancias, pero fija `DATA_PATH=/data/orders.json`, `PORT=8080` y `INSTANCE_ID` (`api-1`, `api-2`), porque dentro del contenedor esos valores son otros. Los datos viven en el volumen `orders-data`, montado como solo lectura.

## Estructura

```
next/
├── Makefile
├── Dockerfile             # imagen multi-stage, corre sin root; el contexto es api/
├── docker-compose.yml     # HAProxy + api-1 + api-2 + volumen de datos
├── haproxy/haproxy.cfg    # balanceador
├── README.md
├── .env.example           # variables de ejemplo (el .env real no se sube)
├── .gitignore
└── api/
    ├── pyproject.toml     # dependencias y comando `next`
    ├── uv.lock            # versiones fijas
    ├── data/orders.json   # datos de ejemplo (no van en la imagen)
    ├── src/next/
    │   ├── main.py          # arma la app y arranca el servidor
    │   ├── routes.py        # endpoints
    │   ├── errors.py        # errores y sus respuestas
    │   ├── data.py          # lectura y validación de los datos
    │   ├── middleware.py    # header X-Instance-Id y log por solicitud
    │   ├── observability.py # logs en JSON
    │   ├── settings.py      # variables de entorno
    │   └── utils.py
    └── tests/
```

Documentación del diseño: `architecture-design/`.
