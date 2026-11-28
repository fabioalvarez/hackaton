# Verificación de requisitos — Nodo Ruta

Generado: 2026-11-28 08:40:09 · **14 de 15 cumplen**

| ID | Qué se comprueba | Esperado | Medido | Resultado |
|---|---|---|---|---|
| RF-01 | Consultar pedidos | los 6 pedidos cargados | 6 pedidos | CUMPLE |
| RF-02 | La respuesta incluye la versión de los datos | la versión de los datos cargados, en el header X-Data-Version | respuesta: v1, cargada: v1 | CUMPLE |
| RF-03 | Página de inicio | 200 con una página HTML que enlaza a las otras páginas | 200, text/html; charset=utf-8, enlaces: /orders, /health | CUMPLE |
| RF-04 | Salud del servicio | 200 y estado ok | 200, {'status': 'ok'} | CUMPLE |
| RF-05 | Cada respuesta indica la instancia que la atendió | ID en el 100 % de las respuestas, y las 2 instancias aparecen | 2 instancias distintas en 30 respuestas | CUMPLE |
| CT-01 | Sin secretos en la imagen ni en el repositorio | ninguno encontrado, y `.env` ignorado por git | 0 hallazgos, `.env` ignorado: sí | CUMPLE |
| CT-02 | Exposición mínima hacia el exterior | solo HAProxy publica un puerto; las instancias no responden directo; sin /docs | publican puerto: ['next-haproxy-1']; acceso directo a la API: no responde; /docs, /redoc, /openapi.json: [404, 404, 404] | CUMPLE |
| TESTS | Tests automáticos (RF, QA-03, QA-04, QA-06, QA-02 y CT) | todos pasan | sin resultado | NO CUMPLE |
| QA-01 | Una instancia se detiene con consultas en curso | ≥ 99 % de solicitudes exitosas; HAProxy deja de enviarle solicitudes en ≤ 10 s | 100.0% de 31 solicitudes; HAProxy la sacó en 0.4 s | CUMPLE |
| QA-02 | Los datos se pierden | restaurados sin intervención en ≤ 5 min; versión y contenido idénticos al respaldo | archivo inválido: 0.2 s; archivo borrado: 1.8 s; coincide con el respaldo de v1: sí | CUMPLE |
| QA-03 | Se recrea un contenedor del servicio | 0 pedidos perdidos o modificados; misma versión antes y después | 0 pedidos perdidos; versión v1 → v1; contenido igual | CUMPLE |
| QA-04 | Se publica una versión que no funciona | servicio restablecido en ≤ 5 min con la versión anterior; 0 pedidos perdidos | descartada en 2 s (salida 1); versión vigente v1; 0 solicitudes fallidas de 32; datos iguales | CUMPLE |
| QA-05 | Crear el despliegue completo desde cero | operativo con las 2 instancias en ≤ 10 min, con un solo comando | 10 s con `make up`; operativo: sí | CUMPLE |
| QA-06 | Diagnosticar el incidente con los logs | instancia afectada identificada en ≤ 120 s; 100 % de las solicitudes asociadas a una instancia | identificada en 0.4 s (log de HAProxy: `Server api/... DOWN`); 31 de 31 solicitudes con instancia conocida | CUMPLE |
| QA-07 | Retirar los recursos al terminar las pruebas | 0 recursos activos en ≤ 15 min; factores de consumo identificados para el 100 % de los componentes | sin recursos en 0.3 s; componentes sin factor documentado: ninguno | CUMPLE |

## RF-05

- instancias vistas: ['6562ce2cfb48', 'de1d1e2c41c7']

## CT-01

- archivos revisados: 49, imagen: next-api:dev

## CT-02

- next-haproxy-1: 0.0.0.0:8000->8080/tcp, [::]:8000->8080/tcp

## QA-01

- instancia detenida: api-1

## QA-02

- hash del respaldo = hash restaurado = 8dab15c00d9939f7...

## QA-04

- despliegue bueno v1: salida 0
- rolled back: the previous version keeps running

## QA-05

- parte de `make down` (sin contenedores ni volumen); no se borran `.env` ni `api/.venv`

## QA-06

- comandos de diagnóstico: `docker compose ps -a` y `docker compose logs haproxy`

## QA-07

- gasto total: 0, todo corre en la máquina local y no se usa ninguna cuenta de nube
- el entorno se vuelve a levantar al terminar
