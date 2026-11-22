# Nodo Ruta · orders API
# Usage: `make help`

PORT    := 8000
API     := api
FILE    ?= store/data/orders.json
VOLUME  := next_orders-data
COMPOSE := docker compose
INSTANCE ?= api-1

.DEFAULT_GOAL := help
.PHONY: help env up-local up down logs load-data corrupt delete-data kill-instance test check-docker

help: ## Show the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-14s %s\n", $$1, $$2}'

# ---------- Environment ----------

env: .env ## Create the environment (api/.venv) and the .env file if missing
	uv sync --directory $(API)

.env:
	cp .env.example .env

# ---------- Run ----------

up-local: env ## Run one API instance without Docker, on http://localhost:8080
	uv run --directory $(API) --env-file $(CURDIR)/.env next

up: .env check-docker ## Run HAProxy + 2 API instances with Docker, on http://localhost:8000
	$(COMPOSE) up --no-start --build

	@$(MAKE) --no-print-directory load-data
	
	$(COMPOSE) up -d --wait

	@echo "Ready: http://localhost:$(PORT)"

down: ## Remove containers, network and data volume
	$(COMPOSE) down -v --remove-orphans

logs: ## Follow the logs of all services
	$(COMPOSE) logs -f -t

load-data: ## Load a data file into the volume (default: store/data/orders.json)
	@test -f "$(FILE)" || { echo "File not found: $(FILE)"; exit 1; }
	docker run --rm -v $(VOLUME):/data -v "$(abspath $(FILE)):/src/orders.json:ro" alpine \
		sh -c 'cp /src/orders.json /data/.orders.tmp && chmod 644 /data/.orders.tmp && mv /data/.orders.tmp /data/orders.json'

check-docker:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is off. Starting it..."; \
		open -a Docker; \
		until docker info >/dev/null 2>&1; do sleep 2; done; \
	}

# ---------- Tests ----------

test: env ## Run the tests
	uv run --directory $(API) pytest tests $(CURDIR)/backup/tests


# ---------- Validation (manual checks against the running environment) ----------

corrupt: ## Corrupt the data file in the volume (to test that the backup restores it)
	docker run --rm -v $(VOLUME):/data alpine sh -c 'echo corrupted > /data/orders.json'

delete-data: ## Delete the data file in the volume (to test that the backup restores it)
	docker run --rm -v $(VOLUME):/data alpine rm /data/orders.json

kill-instance: ## Kill one API instance (INSTANCE=api-1) and check that the service keeps responding
	$(COMPOSE) kill $(INSTANCE)
	@echo "20 requests through HAProxy while $(INSTANCE) is down (count, status, instance):"
	@for i in $$(seq 20); do \
		curl -s -o /dev/null -w "%{http_code} %header{x-instance-id}\n" localhost:$(PORT)/orders; \
	done | sort | uniq -c
