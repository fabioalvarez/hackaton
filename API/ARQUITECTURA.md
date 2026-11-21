# Arquitectura de la API — Nodo Ruta

Arquitectura del servicio que implementa el contrato definido en
[`architecture-design/`](../architecture-design). Este documento describe la
**estructura interna de la API**: sus componentes, el flujo de una solicitud y
cómo cada decisión responde a un requisito funcional (RF), un escenario de
calidad (QA) o un constraint (CT).

El *qué* y el *por qué* de alto nivel viven en `architecture-design/`; aquí va
el *cómo* del servicio.

---

## 1. Propósito y alcance

La API es el **único componente ejecutable** del diseño: un servicio de consulta
de entregas, sin estado, que lee los datos (pedidos + versión) desde un
almacenamiento compartido de solo lectura y los sirve por HTTP.

| Hace | No hace |
|---|---|
| Servir pedidos, página de inicio y salud | Escribir o modificar datos |
| Identificar la instancia que atendió | Autenticar o autorizar |
| Registrar cada solicitud | Procesos en segundo plano / mensajería |
| Tomar su configuración del entorno | Guardar estado entre solicitudes |

El respaldo/restauración, el balanceo, el rollback y la infraestructura **no**
son parte de la API: los aportan componentes externos (ALB, EFS, S3, ECS,
Terraform). La API solo expone los *ganchos* que esos componentes necesitan
(health check, lectura de archivo externo, header de instancia, logs).

---

## 2. Estilo y principios

**Estilo:** servicio HTTP/REST síncrono, sin estado (consecuencia del estilo
*Service-Based* del diseño arquitectónico).

Principios que gobiernan el código:

1. **Sin estado (stateless).** La API no guarda nada en memoria entre
   solicitudes. El archivo de datos se **lee en cada petición**, no al arrancar.
   → habilita réplicas intercambiables (QA-01) y durabilidad ante recreación
   (QA-03).
2. **Configuración externa.** Toda la configuración viene de variables de
   entorno; no hay valores ni secretos en la imagen ni en el repositorio (A7,
   CT-01).
3. **Datos fuera de la aplicación.** La API recibe la **ruta** del archivo, no el
   archivo: así el almacenamiento (EFS/volumen) es un detalle de despliegue
   (patrón *Externalized State*, QA-03).
4. **Una responsabilidad por endpoint.** Cada ruta cubre requisitos concretos y
   es verificable con una prueba del plan.

---

## 3. Componentes internos

```
                         app/
  ┌───────────────────────────────────────────────────────────┐
  │                                                             │
  │   main.py                         config.py                 │
  │   ┌───────────────────────┐       ┌──────────────────────┐  │
  │   │ Middleware HTTP        │◄──────┤ Settings (env vars)  │  │
  │   │  · X-Instance-Id       │       │  · INSTANCE_ID       │  │
  │   │  · log por solicitud   │       │  · DATA_FILE         │  │
  │   └──────────┬─────────────┘       │  · APP_VERSION       │  │
  │              │                     │  · FAIL_HEALTH       │  │
  │   ┌──────────▼─────────────┐       └──────────────────────┘  │
  │   │ Rutas                  │                                 │
  │   │  GET /         inicio  │       leer_datos()              │
  │   │  GET /pedidos ─────────┼──────► lee DATA_FILE en cada    │
  │   │  GET /health           │        solicitud (solo lectura) │
  │   └────────────────────────┘                 │              │
  │                                               ▼              │
  └───────────────────────────────────────────────────────────┘
                                          Almacenamiento externo
                                          (EFS en AWS / volumen local)
                                               data/pedidos.json
```

| Componente | Archivo | Responsabilidad |
|---|---|---|
| **Settings** | `app/config.py` | Lee la configuración del entorno una vez al iniciar. |
| **Middleware** | `app/main.py` | Añade `X-Instance-Id` a toda respuesta y registra cada solicitud (RF-05, A4, A6, QA-06). |
| **Rutas** | `app/main.py` | Los 3 endpoints del contrato. |
| **`leer_datos()`** | `app/main.py` | Lee el archivo de datos en cada solicitud a `/pedidos`. |
| **Datos** | `data/pedidos.json` | Fuente única: pedidos + versión. Externo a la app. |

---

## 4. Flujo de una solicitud

```
Cliente
  │  GET /pedidos
  ▼
Balanceador (ALB / nginx)  ── health check ──► elige una instancia sana
  │
  ▼
Instancia (ECS Fargate / contenedor)
  │
  ├─ Middleware: inicia cronómetro
  │
  ├─ Ruta /pedidos ─► leer_datos() ─► abre DATA_FILE (solo lectura) ─► JSON
  │
  ├─ Middleware: añade header  X-Instance-Id: <id>
  │
  └─ Middleware: escribe log   instance=<id> method=GET path=/pedidos status=200
  ▼
Respuesta  { version, count, pedidos[] }  +  X-Instance-Id
```

- **Síncrono de punta a punta:** el cliente espera la respuesta en la misma
  conexión. No hay colas ni trabajos diferidos.
- **La lectura del archivo ocurre dentro de la solicitud**, no en el arranque:
  si el archivo cambia (nueva versión de datos) o la instancia se recrea, la
  siguiente solicitud ya refleja el estado actual del almacenamiento.

---

## 5. Contrato de la API

| Método y ruta | Respuesta | Códigos | Requisito |
|---|---|---|---|
| `GET /` | Página de inicio (HTML) con instancia y versión | 200 | RF-03 |
| `GET /pedidos` | `{ version, count, pedidos[] }` | 200 | RF-01, RF-02 |
| `GET /health` | `{ "status": "ok" }` / `{ "status": "fail" }` | 200 / 503 | RF-04, QA-01, QA-04 |
| *(todas)* | Header `X-Instance-Id: <id>` | — | RF-05 |

Ejemplo de `GET /pedidos`:

```json
{
  "version": "v1",
  "count": 6,
  "pedidos": [
    { "id": "PED-001", "cliente": "Ferretería El Tornillo",
      "destino": "Carrera 12 #45-30, Bogotá", "estado": "en_ruta",
      "fecha": "2026-11-21" }
  ]
}
```

---

## 6. Modelo de datos

El archivo `data/pedidos.json` es la fuente única. Formato:

```
{
  "version": "<identificador de versión>",   // RF-02
  "pedidos": [                                // RF-01
    { "id", "cliente", "destino", "estado", "fecha" }
  ]
}
```

- **Solo lectura:** la API nunca escribe este archivo → sin escrituras
  concurrentes entre las 2 instancias (P3, P6).
- **La versión viaja con los datos:** restaurar un respaldo restaura también su
  versión, y la comparación de QA-02 es directa.
- Cargar una versión nueva = reemplazar el archivo en el almacenamiento
  compartido; la API no cambia.

---

## 7. Configuración (variables de entorno)

| Variable | Por defecto | Rol arquitectónico |
|---|---|---|
| `DATA_FILE` | `/data/pedidos.json` | Desacopla la app del almacenamiento (EFS vs volumen). |
| `INSTANCE_ID` | *hostname* | Identidad de la réplica (ID de tarea en ECS). |
| `APP_VERSION` | `v1` | Versión de imagen para el rollback (QA-04). |
| `FAIL_HEALTH` | `false` | Gancho de prueba: fuerza una versión "defectuosa". |

Ninguna contiene secretos hoy. Si aparecieran (p. ej. credenciales), irían en
SSM Parameter Store inyectado como entorno, nunca en la imagen (CT-01).

---

## 8. Cómo la API soporta cada atributo de calidad

La API no *implementa* los atributos por sí sola; aporta el gancho que el
componente de infraestructura necesita. Esta es la trazabilidad:

| Escenario | Qué aporta la API | Qué aporta la infraestructura |
|---|---|---|
| **QA-01** Availability | Sin estado + `/health` fiable | ALB reparte y saca la instancia caída |
| **QA-03** Durability | Lee los datos de fuente externa, no los guarda | EFS persiste el archivo |
| **QA-02** Recoverability (datos) | La versión viaja en el archivo | S3 versionado respalda/restaura |
| **QA-04** Recoverability (versión) | `FAIL_HEALTH` → 503; `APP_VERSION` fija | Circuit breaker de ECS hace rollback |
| **QA-06** Observability | `X-Instance-Id` + log por solicitud | CloudWatch Logs agrega y consulta |
| **CT-01** Sin secretos | Config por entorno, nada en la imagen | SSM si hiciera falta |
| **CT-02** Exposición mínima | Escucha solo en su puerto interno | Solo el ALB recibe tráfico externo |

---

## 9. Observabilidad

- **Una línea de log por solicitud**, con formato de pares clave=valor y el
  `instance=<id>` en cada línea (A6, QA-06):

  ```
  2026-11-21 14:05:23 level=INFO instance=instancia-a method=GET path=/pedidos status=200 dur_ms=3.1
  ```

- **Trazabilidad:** toda respuesta lleva `X-Instance-Id`, así que cualquier
  petición observada por el cliente se puede asociar a una instancia (meta de
  QA-06: 100 % trazable, diagnóstico ≤ 2 min).
- Los logs van a *stdout*; el runtime (ECS) los envía a CloudWatch sin que la
  app conozca ese destino.

---

## 10. Topología: local y AWS

La misma imagen corre en ambos entornos; solo cambia lo que la rodea.

| Pieza lógica | Local (`docker-compose`) | AWS (diseño) |
|---|---|---|
| Instancias sin estado | 2 contenedores `instancia-a/-b` | 2 tareas **ECS Fargate** |
| Punto de entrada + salud | **nginx** (`balanceador`) | **ALB** |
| Almacenamiento compartido RO | Volumen `./data:ro` | **EFS** |
| Registro de imágenes | Imagen local | **ECR** |
| Rollback | `FAIL_HEALTH` → 503 (manual) | Circuit breaker de **ECS** |
| Logs | *stdout* | **CloudWatch Logs** |
| Respaldo | Copia del archivo | **S3** con versionado |

```
                 Internet
                    │
            ┌───────▼────────┐
            │  ALB / nginx   │  health check
            └───┬────────┬───┘
                │        │
        ┌───────▼─┐   ┌──▼──────┐
        │ inst. A │   │ inst. B │   (ECS Fargate / contenedores, sin estado)
        └────┬────┘   └────┬────┘
             │  solo lectura │
             └──────┬────────┘
                    ▼
            ┌───────────────┐        ┌──────────────┐
            │ EFS / volumen │ ──────►│ S3 (respaldo)│
            │ pedidos.json  │        └──────────────┘
            └───────────────┘
```

---

## 11. Límites y decisiones

- **Un solo servicio, no microservicios:** no hay dominios que separar (6
  pedidos, solo lectura). Añadir servicios sería complejidad sin beneficio.
- **Sin base de datos:** un archivo cumple todos los requerimientos de
  persistencia (P1–P8) sin cambiar el código ni agregar un componente.
- **Sin caché en memoria:** se prefiere releer el archivo (es diminuto) a cachear,
  para no introducir estado ni inconsistencias entre réplicas.
- **Sin escritura:** la API es de solo lectura; cargar datos nuevos es una
  operación de despliegue, no del servicio.

Estas decisiones mantienen la API **pequeña, reemplazable y recuperable**, que es
exactamente lo que el reto pide demostrar.
