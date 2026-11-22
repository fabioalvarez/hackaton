# Nodo Ruta · orders API
# Usage: `make help`

PORT    := 8000
API     := api
FILE    ?= store/data/orders.json
VOLUME  := next_orders-data
COMPOSE := docker compose

# Version of the image that runs: the last one deployed (`make deploy`), or `dev`.
TAG     ?= $(shell tail -n 1 .deploy-history 2>/dev/null || echo dev)
export TAG

.DEFAULT_GOAL := help
.PHONY: help env up-local up down logs load-data deploy corrupt delete-data kill-instance deploy-broken verify test check-docker

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

up: .env check-docker ## Run HAProxy + 2 API replicas with Docker, on http://localhost:8000
	$(COMPOSE) up --no-start --build

	@$(MAKE) --no-print-directory load-data

	$(COMPOSE) up -d --wait

	@# HAProxy needs a few seconds to find the replicas: it is ready when it answers.
	@for i in $$(seq 60); do curl -sf localhost:$(PORT)/health >/dev/null && break; sleep 1; done
	@curl -sf localhost:$(PORT)/health >/dev/null || { echo "HAProxy does not answer on port $(PORT)"; exit 1; }

	@echo "Ready: http://localhost:$(PORT)"

down: ## Remove containers, network and data volume
	$(COMPOSE) down -v --remove-orphans

logs: ## Follow the logs of all services
	$(COMPOSE) logs -f -t

load-data: ## Load a data file into the volume (default: store/data/orders.json)
	@test -f "$(FILE)" || { echo "File not found: $(FILE)"; exit 1; }
	docker run --rm -v $(VOLUME):/data -v "$(abspath $(FILE)):/src/orders.json:ro" alpine \
		sh -c 'cp /src/orders.json /data/.orders.tmp && chmod 644 /data/.orders.tmp && mv /data/.orders.tmp /data/orders.json'

deploy: .env check-docker ## Deploy a new version next to the current one: make deploy TAG=1.1.0
	@test "$(origin TAG)" = "command line" || { echo "Usage: make deploy TAG=1.1.0"; exit 1; }
	python3 deploy/src/main.py $(TAG) $(if $(BREAK),--break)

check-docker:
	@docker info >/dev/null 2>&1 || { \
		echo "Docker is off. Starting it..."; \
		open -a Docker; \
		until docker info >/dev/null 2>&1; do sleep 2; done; \
	}

# ---------- Tests ----------

test: env ## Run the tests
	uv run --directory $(API) pytest tests $(CURDIR)/backup/tests $(CURDIR)/deploy/tests $(CURDIR)/verify/tests


# ---------- Validation (manual checks against the running environment) ----------

corrupt: ## Corrupt the data file in the volume (to test that the backup restores it)
	docker run --rm -v $(VOLUME):/data alpine sh -c 'echo corrupted > /data/orders.json'

delete-data: ## Delete the data file in the volume (to test that the backup restores it)
	docker run --rm -v $(VOLUME):/data alpine rm /data/orders.json

kill-instance: ## Kill one API container and check that the service keeps responding
	docker kill $$($(COMPOSE) ps -q api | head -1)
	@echo "20 requests through HAProxy right after the kill (count, status, instance):"
	@for i in $$(seq 20); do \
		curl -s -o /dev/null -w "%{http_code} %header{x-instance-id}\n" localhost:$(PORT)/orders; \
	done | sort | uniq -c

deploy-broken: ## Deploy a version that cannot start and check that it is rolled back
	-$(MAKE) --no-print-directory deploy TAG=broken BREAK=1
	@echo "20 requests after the rolled back deploy (count, status):"
	@for i in $$(seq 20); do curl -s -o /dev/null -w "%{http_code}\n" localhost:$(PORT)/orders; done | sort | uniq -c

verify: ## Check every requirement and quality scenario: make verify (YES=1 skips the question, STEP=1 waits for Enter before each scenario, ONLY=QA-01,RF-02 picks some)
	python3 verify/src/main.py $(if $(YES),--yes) $(if $(STEP),--step) $(if $(ONLY),--only $(ONLY))
