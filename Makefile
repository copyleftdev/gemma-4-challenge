SHELL := /bin/sh

CARE_COMPASS_MODEL ?= gemma4:e2b
CARE_COMPASS_PORT ?= 8080
OLLAMA_MODE ?= container
OLLAMA_GPU ?= auto
OPEN_BROWSER ?= 1

export CARE_COMPASS_MODEL
export CARE_COMPASS_PORT
export OLLAMA_MODE
export OLLAMA_GPU
export DEMO_URL
export OPEN_BROWSER

.PHONY: demo doctor stop logs status

demo:
	@scripts/demo.sh

doctor:
	@scripts/doctor.sh

stop:
	@docker compose down

logs:
	@docker compose logs -f care-compass

status:
	@port="$$(docker compose port care-compass 8080 2>/dev/null | awk -F: 'END {print $$NF}')"; \
	if [ -z "$$port" ]; then port="$(CARE_COMPASS_PORT)"; fi; \
	curl -fsS "http://127.0.0.1:$$port/api/status"
