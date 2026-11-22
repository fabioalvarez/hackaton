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
| `make up` | Levanta con Docker **HAProxy y 2 réplicas de la API** en http://localhost:8000. Si Docker está apagado, lo inicia. Termina cuando HAProxy ya responde `/health`, no antes. Carga `store/data/orders.json` en el volumen si está vacío |
| `make down` | Elimina contenedores, red y volumen de datos |
| `make logs` | Sigue los logs de HAProxy y de las 2 instancias |
| `make load-data FILE=ruta` | Reemplaza el archivo de datos del volumen por el indicado |
| `make corrupt` | Deja inválido el archivo de datos del volumen, para probar que el respaldo lo restaura |
| `make delete-data` | Borra el archivo de datos del volumen, para probar que el respaldo lo restaura |
| `make deploy TAG=1.1.0` | Despliega una versión nueva: levanta 2 contenedores al lado de los actuales y apaga los actuales solo si los nuevos funcionan. Si fallan, los descarta y el servicio no se interrumpe |
| `make kill-instance` | Mata un contenedor de la API y comprueba que el servicio sigue respondiendo |
| `make verify` | Demuestra todos los requisitos y escenarios de calidad contra el entorno levantado, mostrando en vivo lo que pasa, y escribe `reports/verification.md`. `YES=1` no pregunta antes de las comprobaciones destructivas; `STEP=1` espera un Enter antes de cada escenario; `ONLY=QA-01,RF-02` ejecuta solo algunas |
| `make deploy-broken` | Despliega una versión que no arranca y comprueba que se descarta sin afectar el servicio |
| `make test` | Ejecuta las pruebas de la API y del vigilante de respaldo |

Con `make up`, la API solo se alcanza por HAProxy (puerto `8000`); las instancias no publican puerto. El header `X-Instance-Id` indica cuál respondió (el ID de su contenedor).

```bash
for i in $(seq 10); do curl -s -o /dev/null -D - localhost:8000/orders | grep -i x-instance-id; done | sort | uniq -c
```

## Respaldo y restauración

Con `make up` corre un contenedor `backup` que revisa los datos cada 5 s, sin intervención:

- **Respaldo:** cuando los datos son válidos y nuevos (versión nueva) o distintos del respaldo de su versión, los copia a `store/backups/orders-<versión>.json`. Un cambio en datos válidos es una actualización, no una pérdida.
- **Restauración:** solo si los datos se pierden: el archivo falta o es inválido. Se restaura la última versión respaldada desde `store/backups/`.
- **Ver qué valida:** con `LOG_LEVEL: debug` (el valor actual en `docker-compose.yml`), cada revisión imprime qué hizo (`starting backup process`, `data file is the same as the backup of v1, no backup is required`). Con `info` solo se ven los respaldos y las restauraciones.
- **Probarlo:** `make corrupt` o `make delete-data` hacen perder los datos; en unos segundos `make logs` muestra `restore_ok` y `/orders` vuelve a responder igual.

`store/backups/` queda en tu máquina (ignorado por git) y `make down` no lo borra.

## Verificación de requisitos

`make verify` demuestra que se cumplen los requisitos funcionales, los escenarios de calidad y los constraints, y lo hace **mostrando en vivo lo que pasa**. De cada escenario dice primero qué va a hacer y cuál es el criterio (≥ 99 % de éxito, ≤ 10 s, ≤ 5 min, etc.). Mientras corre muestra:

- **Cada llamada a la API:** hora, ruta, código y qué instancia respondió.
- **Lo que le pasa al entorno:** cuando se detiene o se crea un contenedor, cuando HAProxy saca o reincorpora una instancia, cuando el vigilante restaura los datos, y los pasos del despliegue.
- **El veredicto de cada escenario**, con lo medido, y un resumen al final.

```
14:00:03  ⚡ detengo la instancia api-1 de golpe (docker kill)
14:00:03  🔻 api-1 se detuvo
14:00:04  🔻 HAProxy: una instancia ya no existe, deja de recibir solicitudes
14:00:04  ✅ GET /orders  200  atendió api-2
14:00:19  ✅ QA-01: 100.0% de 32 solicitudes; HAProxy la sacó en 0.6 s
```

Con `STEP=1` se detiene antes de cada escenario para que quien presenta lo explique. Además escribe `reports/verification.md` con la evidencia.

Las comprobaciones de calidad **cambian el entorno**: matan y recrean contenedores, rompen los datos, despliegan versiones y lo bajan y levantan por completo. Al terminar el entorno queda levantado, pero el volumen de datos vuelve a los datos iniciales (`store/data/orders.json`): lo que hayas cargado con `make load-data` se pierde. Los respaldos de `store/backups/` no se borran. Por eso pregunta antes de empezar; `YES=1` omite la pregunta. Necesita el entorno levantado (`make up`).

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
- `make up` pasa el `.env` a las instancias, pero fija `DATA_PATH=/data/orders.json` y `PORT=8080`, porque dentro del contenedor esos valores son otros. El `INSTANCE_ID` de cada una es el ID de su contenedor. Los datos viven en el volumen `orders-data`, montado como solo lectura.

## Estructura

```
next/
├── Makefile
├── docker-compose.yml     # HAProxy + api (2 réplicas) + backup + volumen de datos
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
│   ├── src/
│   │   ├── main.py          # bucle: revisa los datos cada 5 s
│   │   ├── watcher.py       # decide cuándo respaldar y cuándo restaurar
│   │   ├── validation.py    # validación del archivo de datos
│   │   ├── utils.py         # funciones auxiliares (hash, lectura, reemplazo atómico)
│   │   ├── logs.py          # una línea JSON por evento
│   │   └── settings.py      # variables de entorno
│   └── tests/
├── verify/                # herramienta que demuestra los requisitos (Python)
│   ├── src/
│   │   ├── main.py            # elige las comprobaciones, las ejecuta y escribe el informe
│   │   ├── checks_functional.py   # RF-01 a RF-05
│   │   ├── checks_quality.py      # QA-01 a QA-07 (cambian el entorno)
│   │   ├── checks_constraints.py  # CT-01, CT-02 y los tests automáticos
│   │   ├── system.py          # docker, balanceador y archivos
│   │   ├── result.py          # lo que reporta cada comprobación
│   │   └── report.py          # tabla en la terminal e informe en Markdown
│   └── tests/
├── deploy/                # script de despliegue (Python)
│   ├── src/
│   │   ├── main.py          # recibe la etiqueta y arranca el despliegue
│   │   ├── deployer.py      # el flujo: crear, esperar, mantener o descartar
│   │   └── docker.py        # llamadas a docker
│   └── tests/
├── haproxy/haproxy.cfg    # balanceador
└── store/                 # todos los datos
    ├── data/orders.json   # datos iniciales (se cargan al volumen; no van en las imágenes)
    └── backups/           # respaldos (ignorados por git)
```

Documentación del diseño: `architecture-design/`.
