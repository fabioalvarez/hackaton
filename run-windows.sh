#!/usr/bin/env bash
# Equivalente a los comandos `make` para Windows (Git Bash).
#
# El Makefile original no funciona en Windows por dos motivos:
#   1. Sus recetas estan escritas en bash (for, curl, sleep) y, al llamar al
#      sub-make, $(MAKE) se expande a la ruta "C:/Program Files (x86)/GnuWin32/bin/make";
#      el "(x86)" sin comillas rompe el shell.
#   2. `check-docker` usa `open -a Docker`, un comando exclusivo de macOS.
# Este script corre los mismos pasos con `docker compose` directamente desde Git Bash.
#
# Uso (desde Git Bash, en la raiz del repo):
#   bash run-windows.sh up        # construye y levanta todo en http://localhost:8000
#   bash run-windows.sh down      # apaga y borra contenedores, red y volumen
#   bash run-windows.sh logs      # sigue los logs en vivo
#   bash run-windows.sh load-data # recarga store/data/orders.json en el volumen
#   bash run-windows.sh test      # corre las pruebas dentro de Docker

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$ROOT_DIR/next"
COMPOSE=(docker compose -f "$APP_DIR/docker-compose.yml")
VOLUME="next_orders-data"
PORT="8000"

ensure_env() {
  if [ ! -f "$APP_DIR/.env" ]; then
    cp "$APP_DIR/.env.example" "$APP_DIR/.env"
    echo "Creado next/.env a partir de .env.example"
  fi
}

check_docker() {
  if ! docker info >/dev/null 2>&1; then
    echo "Docker no esta corriendo. Abre Docker Desktop y vuelve a intentar." >&2
    exit 1
  fi
}

load_data() {
  local file="$APP_DIR/store/data/orders.json"
  [ -f "$file" ] || { echo "No existe el archivo de datos: $file" >&2; exit 1; }
  MSYS_NO_PATHCONV=1 docker run --rm \
    -v "$VOLUME:/data" \
    -v "$file:/src/orders.json:ro" \
    alpine sh -c 'cp /src/orders.json /data/.orders.tmp && chmod 644 /data/.orders.tmp && mv /data/.orders.tmp /data/orders.json'
  echo "Datos cargados en el volumen $VOLUME"
}

up() {
  ensure_env
  check_docker
  "${COMPOSE[@]}" up --no-start --build
  load_data
  "${COMPOSE[@]}" up -d --wait
  for _ in $(seq 60); do curl -sf "localhost:$PORT/health" >/dev/null && break; sleep 1; done
  curl -sf "localhost:$PORT/health" >/dev/null || { echo "HAProxy no responde en el puerto $PORT" >&2; exit 1; }
  echo "Listo: http://localhost:$PORT"
}

down() { "${COMPOSE[@]}" down -v --remove-orphans; }
logs() { "${COMPOSE[@]}" logs -f -t; }

run_tests() {
  check_docker
  docker build -q -f "$APP_DIR/tests.Dockerfile" -t next-tests "$ROOT_DIR"
  docker run --rm next-tests
}

cmd="${1:-up}"
case "$cmd" in
  up)        up ;;
  down)      down ;;
  logs)      logs ;;
  load-data) load_data ;;
  test)      run_tests ;;
  *) echo "Comando desconocido: $cmd (usa: up | down | logs | load-data | test)" >&2; exit 1 ;;
esac
