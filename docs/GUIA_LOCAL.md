# Nodo Ruta en local — guía de despliegue y pruebas

Despliegue completo en un solo computador, siguiendo la vista de despliegue del equipo. Todos los comandos se ejecutan desde `recursos/`. En Windows pueden usar `py` en lugar de `python`.

## Arquitectura: AWS planteado → equivalente local

| Vista de despliegue (AWS) | Local | Parámetros |
|---|---|---|
| ALB, punto de entrada único | `proxy` (NGINX) en `127.0.0.1:8080` | 2 fallos sacan la instancia por 10 s |
| ECS Fargate, 2 tareas | `app1` y `app2` | 0,25 CPU y 512 MB cada una; health check cada 5 s, 2 fallos |
| EFS en solo lectura | Carpeta `data/` montada en `/data` con `read_only` | Ambas instancias leen el mismo archivo |
| S3 con versionado | Carpeta `respaldos/` (JSON + huella SHA-256) | Un respaldo por versión, nunca se sobrescribe |
| ECR, últimas 5 imágenes | Imágenes locales `nodo-ruta:<version>` | `desplegar.py` borra las que pasen de 5 |
| Circuit breaker de ECS | `scripts/desplegar.py desplegar` | Mínimo 100 %, máximo 200 %, rollback ≤ 5 min |
| CloudWatch Logs | `docker compose logs` | Rotación de 10 MB × 3 archivos |
| GitHub Actions | `.github/workflows/ci.yml` | Ejecuta todas las pruebas en cada PR |

Archivos: `local/compose.yaml`, `local/nginx.conf`, `scripts/desplegar.py`. La versión activa queda en `local/.env`.

Límite que hay que declarar: todo corre en un computador, así que el equipo, el proxy y la carpeta `data/` siguen siendo puntos únicos de fallo. En AWS los resolverían el ALB en 2 zonas, EFS y S3.

## 1. Preparación

Requisitos: Python 3 y Docker Desktop **encendido** (`docker version` debe mostrar *Server*).

```text
python scripts/datos.py preparar
python scripts/desplegar.py construir v1
python scripts/desplegar.py iniciar
```

Abran http://127.0.0.1:8080/health y http://127.0.0.1:8080/pedidos.

## 2. Pruebas de la guía del reto

### I01 — Acceso común con las 2 instancias (PR-01)
```text
python scripts/verificar_servicio.py --esperadas app1,app2 --salida evidencias/inicio.json
```

### I02 — Detener una instancia (PR-02)
```text
docker compose -f local/compose.yaml stop app1
python scripts/verificar_servicio.py --esperadas app2 --salida evidencias/fallo_app1.json
```
Registren la hora de detención y los errores que aparezcan.

### I03 — Recuperar la instancia
```text
docker compose -f local/compose.yaml start app1
python scripts/verificar_servicio.py --esperadas app1,app2 --salida evidencias/recuperado.json
```

### I04 — Recrear y conservar los datos (PR-03)
```text
docker compose -f local/compose.yaml up -d --force-recreate app1
python scripts/verificar_servicio.py --esperadas app1,app2 --salida evidencias/recreado.json
```
La versión y los 6 pedidos deben ser los mismos.

### I05 — Respaldar, alterar y restaurar (PR-04)
```text
python scripts/datos.py respaldar
python scripts/datos.py simular-error
python scripts/verificar_servicio.py --salida evidencias/datos_alterados.json
python scripts/datos.py restaurar --respaldo respaldos/ARCHIVO.json
python scripts/verificar_servicio.py --esperadas app1,app2 --salida evidencias/restaurado.json
```
Con los datos alterados, las 2 instancias devuelven 503: el fallo es compartido. Midan el tiempo hasta restaurar (meta ≤ 5 min).

### PR-05 — Versión defectuosa y rollback automático (QA-04)
```text
python scripts/desplegar.py construir v2-rota --falla
python scripts/desplegar.py desplegar v2-rota
python scripts/desplegar.py estado
```
El script lanza 2 candidatas junto a las activas y revisa su salud cada 5 s. Con 2 fallos seguidos las retira y deja la versión anterior sin tocarla. El JSON de evidencia queda en `evidencias/despliegue-v2-rota-*.json`.

Para una versión sana:
```text
python scripts/desplegar.py construir v2
python scripts/desplegar.py desplegar v2
```
Si las candidatas pasan 2 health checks, se reemplaza `app1` y luego `app2`, siempre con al menos una instancia atendiendo.

### PR-07 — Diagnóstico con registros (QA-06)
```text
docker compose -f local/compose.yaml logs --tail 50
```
En el proxy, `upstream=` indica qué instancia atendió cada solicitud y con qué código respondió.

### I06 / PR-06 — Repetir con otro integrante
Otro integrante clona el repositorio y sigue esta guía desde el paso 1, cronometrando.

### PR-09 y PR-10 — Secretos y exposición
No hay credenciales en la imagen ni en el repositorio. Solo se publica `127.0.0.1:8080` (el proxy); `app1` y `app2` no tienen puertos publicados en el equipo.

## 3. GitHub Actions

`ci.yml` corre en cada PR y en cada push a `main`, y repite automáticamente I01, I02, I05, PR-05 y el despliegue de una versión sana. Las evidencias quedan en el artefacto `evidencias-ci` de cada ejecución.

Para trabajar en equipo: protejan `main` (Settings → Branches), exijan el check `despliegue-local` y que cada quien trabaje en su rama `feature/...`.

## 4. Limpieza

```text
docker compose -f local/compose.yaml down
```
Se conservan `data/`, `respaldos/` y `evidencias/`.
