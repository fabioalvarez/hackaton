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
| `make up` | Levanta con Docker **HAProxy y 2 instancias** (`api-1`, `api-2`) en http://localhost:8000. Si Docker está apagado, lo inicia y espera a que esté listo. Carga `store/data/orders.json` en el volumen si está vacío |
| `make down` | Elimina contenedores, red y volumen de datos |
| `make logs` | Sigue los logs de HAProxy y de las 2 instancias |
| `make load-data FILE=ruta` | Reemplaza el archivo de datos del volumen por el indicado |
| `make corrupt` | Altera los datos del volumen sin cambiar la versión, para probar el respaldo |
| `make test` | Ejecuta las pruebas de la API y del vigilante de respaldo |

Con `make up`, la API solo se alcanza por HAProxy (puerto `8000`); las instancias no publican puerto. El header `X-Instance-Id` indica cuál respondió: `api-1` o `api-2`.

```bash
for i in $(seq 10); do curl -s -o /dev/null -D - localhost:8000/orders | grep -i x-instance-id; done | sort | uniq -c
```

## Respaldo y restauración

Con `make up` corre un contenedor `backup` que revisa los datos cada 5 s, sin intervención:

- **Respaldo:** cuando aparece una versión nueva y válida, la copia a `store/backups/orders-<versión>.json`.
- **Restauración:** si el archivo falta, es inválido o su contenido cambió sin cambiar la versión, lo restaura desde `store/backups/`.
- **Regla de versiones:** una `data_version` identifica un contenido único. Si cambias los datos, cambia también la versión; de lo contrario se interpreta como una alteración y se revierte.
- **Probarlo:** `make corrupt` altera los datos; en unos segundos `make logs` muestra `restore_ok` y `/orders` vuelve a responder igual.

`store/backups/` queda en tu máquina (ignorado por git) y `make down` no lo borra.

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
├── docker-compose.yml     # HAProxy + api-1 + api-2 + backup + volumen de datos
├── README.md
├── .env.example           # variables de ejemplo (el .env real no se sube)
├── .gitignore
├── api/                   # la API
│   ├── Dockerfile         # imagen multi-stage, corre sin root; el contexto es api/
│   ├── pyproject.toml     # dependencias y comando `next`
│   ├── uv.lock            # versiones fijas
│   ├── src/next/
│   │   ├── main.py          # arma la app y arranca el servidor
│   │   ├── routes.py        # endpoints
│   │   ├── errors.py        # errores y sus respuestas
│   │   ├── data.py          # lectura y validación de los datos
│   │   ├── middleware.py    # header X-Instance-Id y log por solicitud
│   │   ├── observability.py # logs en JSON
│   │   ├── settings.py      # variables de entorno
│   │   └── utils.py
│   └── tests/
├── backup/                # vigilante de respaldo
│   ├── Dockerfile
│   ├── watch.sh
│   └── tests/
├── haproxy/haproxy.cfg    # balanceador
└── store/                 # todos los datos
    ├── data/orders.json   # datos iniciales (se cargan al volumen; no van en las imágenes)
    └── backups/           # respaldos (ignorados por git)
```

Documentación del diseño: `architecture-design/`.
