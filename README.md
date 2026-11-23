# Nodo Ruta · API de pedidos

Servicio de consulta de entregas. Solo lectura: lee los pedidos de un archivo JSON y los expone por HTTP. Detrás de un balanceador, con 2 instancias, respaldo automático de los datos y despliegue con rollback.

Todos los comandos se ejecutan desde la raíz del repositorio. `make help` muestra la lista completa.

## Requisitos

- [Docker](https://www.docker.com/) (si está apagado, `make up` lo inicia en macOS)
- [uv](https://docs.astral.sh/uv/) (para las pruebas y para correr la API sin Docker)
- `make`

## 1. Cómo levantar en local

```bash
make up
```

Construye las imágenes y levanta HAProxy, 2 réplicas de la API y el vigilante de respaldo. Termina cuando el servicio ya responde. La primera vez crea `next/.env` a partir de `next/.env.example`.

La API queda en **http://localhost:8000** (por HAProxy; las instancias no publican puerto). **Ábrela en el navegador:** la página de inicio enlaza a Orders y Health. También por consola:

```bash
curl -s http://localhost:8000/orders | jq                       # los pedidos
curl -si http://localhost:8000/orders | grep -i x-data-version   # la versión de los datos
curl -s http://localhost:8000/health | jq
```

Para ver el reparto entre las 2 instancias (el header `X-Instance-Id` dice cuál respondió):

```bash
for i in $(seq 10); do curl -s -o /dev/null -D - localhost:8000/orders | grep -i x-instance-id; done | sort | uniq -c
```

Para ver los logs y para apagar todo:

```bash
make logs     # HAProxy, las instancias y el vigilante, en vivo
make down     # elimina contenedores, red y volumen de datos
```

**Sin Docker:** `make up-local` levanta **una** instancia en http://localhost:8080.

## 2. Cómo correr las pruebas

**Pruebas automáticas** (no necesitan el entorno levantado):

```bash
make test
```

**Demostración de todos los requisitos** contra el entorno real (necesita `make up` antes):

```bash
make verify
```

Comprueba los requisitos funcionales (RF-01 a RF-05), los escenarios de calidad (QA-01 a QA-07) y los constraints (CT-01, CT-02), y lo hace **mostrando en vivo lo que pasa**: cada llamada a la API y qué instancia respondió, los contenedores que caen o se crean, HAProxy sacando y reincorporando instancias, el vigilante restaurando los datos, y los pasos del despliegue. De cada escenario dice primero qué va a hacer y cuál es el criterio, y al final muestra el veredicto con lo medido.

```
14:00:03  ⚡ detengo la instancia api-1 de golpe (docker kill)
14:00:03  🔻 api-1 se detuvo
14:00:04  🔻 HAProxy: una instancia ya no existe, deja de recibir solicitudes
14:00:04  ✅ GET /orders  200  atendió api-2
14:00:19  ✅ QA-01: 100.0% de 32 solicitudes; HAProxy la sacó en 0.6 s
```

| Opción | Qué hace |
|---|---|
| `make verify STEP=1` | Espera un Enter antes de cada escenario, para que quien presenta lo explique |
| `make verify ONLY=QA-01,RF-02` | Ejecuta solo esos requisitos |
| `make verify YES=1` | No pregunta antes de empezar |

Los escenarios de calidad **cambian el entorno**: matan y recrean contenedores, rompen los datos, despliegan versiones y lo bajan y levantan por completo. Al terminar queda levantado, pero el volumen de datos vuelve a los datos iniciales (`next/store/data/orders.json`): lo que hayas cargado con `make load-data` se pierde. Los respaldos de `next/store/backups/` no se borran. Una ejecución completa escribe `validations/verification.md` con la evidencia (se versiona: es la evidencia de las pruebas). Una ejecución parcial (`ONLY=`) no actualiza el informe.

**Pruebas manuales sueltas**, contra el entorno levantado:

| Comando | Qué prueba |
|---|---|
| `make kill-instance` | Mata un contenedor de la API y comprueba que el servicio sigue respondiendo |
| `make corrupt` | Deja inválido el archivo de datos: el vigilante debe restaurarlo |
| `make delete-data` | Borra el archivo de datos: el vigilante debe restaurarlo |
| `make deploy-broken` | Despliega una versión que no arranca: debe descartarse sin afectar el servicio |

## Todos los comandos

| Comando | Qué hace |
|---|---|
| `make up` | Levanta HAProxy y 2 réplicas con Docker, en http://localhost:8000 |
| `make down` | Elimina contenedores, red y volumen de datos |
| `make logs` | Sigue los logs de todos los servicios |
| `make up-local` | Levanta una instancia sin Docker, en http://localhost:8080 |
| `make env` | Crea el entorno `next/api/.venv` y `next/.env` si faltan |
| `make load-data FILE=ruta` | Reemplaza el archivo de datos del volumen por el indicado |
| `make deploy TAG=1.1.0` | Despliega una versión nueva sin cortar el servicio (ver más abajo) |
| `make test` | Pruebas automáticas |
| `make verify` | Demostración de los requisitos, en la terminal |
| `make kill-instance`, `corrupt`, `delete-data`, `deploy-broken` | Pruebas manuales |

## Despliegue de una versión nueva

```bash
make deploy TAG=1.1.0
```

Construye la imagen y crea 2 contenedores nuevos **al lado** de los actuales. Si los nuevos quedan sanos y HAProxy ya les envía tráfico, elimina los viejos. Si no arrancan o no quedan sanos, elimina los nuevos, muestra sus logs y los viejos siguen atendiendo: el servicio no se interrumpe. La versión vigente queda en `next/.deploy-history`, y `make up` la usa. Para ver el descarte: `make deploy-broken`.

## Respaldo y restauración

Con `make up` corre un contenedor `backup` que revisa los datos cada 5 s, sin intervención:

- **Respaldo:** cuando los datos son válidos y nuevos (versión nueva) o distintos del respaldo de su versión, los copia a `next/store/backups/orders-<versión>.json`. Un cambio en datos válidos es una actualización, no una pérdida.
- **Restauración:** solo si los datos se pierden: el archivo falta o es inválido. Se restaura la última versión respaldada.
- **Ver qué hace:** `make logs` (con `LOG_LEVEL: debug` en `next/docker-compose.yml` también muestra qué valida cada revisión; con `info`, solo los respaldos y las restauraciones).

`next/store/backups/` queda en tu máquina (ignorado por git) y `make down` no lo borra.

## Endpoints

| Ruta | Respuesta |
|---|---|
| `GET /` | Página de inicio (HTML): confirma el servicio y enlaza a las demás páginas |
| `GET /health` | `{"status": "ok"}` y el header `X-Data-Version`; `503` si los datos no se pueden leer |
| `GET /orders` | Los pedidos y, en el header `X-Data-Version`, la versión de los datos; `503` si los datos no se pueden leer |

`/orders` y `/health` responden **JSON a un programa** (`curl`) y **una página a un navegador**: ábrelos en el navegador para verlos como página. Cada dato viaja en un solo sitio: toda respuesta incluye el header `X-Instance-Id` con la instancia que la atendió (el ID de su contenedor), y `/orders` y `/health` incluyen `X-Data-Version` con la versión de los datos. El cuerpo no los repite; para ver los headers: `curl -i`.

## Configuración

Variables de entorno (ninguna es un secreto):

| Variable | Por defecto | Uso |
|---|---|---|
| `DATA_PATH` | `/data/orders.json` | Archivo de datos |
| `INSTANCE_ID` | nombre del host | Identificador de la instancia |
| `SERVICE_NAME` | `Next` | Nombre que muestra `GET /` |
| `PORT` | `8080` | Puerto de escucha |
| `LOG_LEVEL` | `info` | Nivel de logs (`debug` muestra también los `/health` correctos) |

Se leen de las variables de entorno y, si no están, de `next/.env` (copia local de `next/.env.example`, ignorado por git y fuera del contexto de Docker). `make up` pasa ese archivo a las instancias, pero fija `DATA_PATH=/data/orders.json` y `PORT=8080`, porque dentro del contenedor esos valores son otros.

## Estructura

```
.
├── Makefile                   # todos los comandos
├── README.md
├── architecture-design/       # el diseño: requisitos, arquitectura, componentes y plan de pruebas,
│                              # y las vistas: C&C.drawio (componentes y conectores) y deploy view.drawio (despliegue local)
├── validations/               # evidencia de las pruebas: verification.md (lo escribe make verify)
└── next/
    ├── docker-compose.yml     # HAProxy + api (2 réplicas) + backup + volumen de datos
    ├── .env.example           # variables de ejemplo (el .env real no se sube)
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
    │   │   └── pages.py         # las páginas HTML: Home, Orders y Health
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
    ├── deploy/                # script de despliegue (Python)
    │   ├── src/
    │   │   ├── main.py          # recibe la etiqueta y arranca el despliegue
    │   │   ├── deployer.py      # el flujo: crear, esperar, mantener o descartar
    │   │   └── docker.py        # llamadas a docker
    │   └── tests/
    ├── verify/                # herramienta que demuestra los requisitos (Python)
    │   ├── src/
    │   │   ├── main.py              # elige las pruebas, las ejecuta y escribe el informe
    │   │   ├── checks_functional.py     # RF-01 a RF-05
    │   │   ├── checks_constraints.py    # CT-01, CT-02 y los tests automáticos
    │   │   ├── checks_quality.py        # QA-01 a QA-07 (cambian el entorno)
    │   │   ├── commands.py          # ejecuta comandos como lo hace make
    │   │   ├── service.py           # habla con el servicio y espera
    │   │   ├── environment.py       # contenedores, datos y el log de HAProxy
    │   │   ├── live.py              # lo que se imprime mientras corren
    │   │   ├── watching.py          # cuenta lo que hace el entorno: contenedores, HAProxy, vigilante
    │   │   ├── result.py            # qué es un requisito y qué reporta una prueba
    │   │   └── report.py            # resumen e informe en Markdown
    │   └── tests/
    ├── haproxy/haproxy.cfg    # balanceador
    └── store/                 # todos los datos
        ├── data/orders.json   # datos iniciales (se cargan al volumen; no van en las imágenes)
        └── backups/           # respaldos (ignorados por git)
```
