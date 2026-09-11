VENV ?= $(HOME)/Envs/airports
PYTHON := $(VENV)/bin/python3
PYTEST := $(VENV)/bin/pytest
UVICORN := $(VENV)/bin/uvicorn
RUFF := $(VENV)/bin/ruff

IMAGE_NAME ?= airports                ## Docker image name
IMAGE_TAG  ?= latest                  ## Docker image tag
PORT       ?= 8181                    ## Server port
KIOSK_DWELL_SECONDS ?= 2              ## Seconds between kiosk rotations

.PHONY: help run test lint format build docker-run

help: ## Display available targets
	@echo "\033[36mUsage: make [target]\033[0m"
	@echo
	@echo "\033[36mAvailable targets:\033[0m"
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z0-9_-]+:.*## / {printf "  \033[36m%-28s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo
	@echo "\033[36mVariables (and defaults):\033[0m"
	@awk '/^[A-Z_-]+[ 	]*\?=.*## / { \
		name=$$0; sub(/[ 	]*\?=.*/,"",name); \
		def=$$0;  sub(/^[^?]*\?=[ 	]*/,"",def); sub(/[ 	]*##.*/,"",def); \
		desc=$$0; sub(/.*##[ 	]*/,"",desc); \
		if (def=="") def="(none)"; \
		printf "  \033[36m%-28s\033[0m %s (default: %s)\n", name, desc, def; \
	}' $(MAKEFILE_LIST)

run: ## Start the dev server with hot reload
	KIOSK_DWELL_SECONDS=$(strip $(KIOSK_DWELL_SECONDS)) $(UVICORN) app.main:app --host 0.0.0.0 --port $(strip $(PORT)) --reload

test: ## Run the test suite
	$(PYTEST) --verbose test_*.py

format: ## Auto-format and fix lint violations
	$(RUFF) format app/ test_*.py
	$(RUFF) check --fix app/ test_*.py

lint: ## Verify formatting and lint (no changes)
	$(RUFF) format --check app/ test_*.py
	$(RUFF) check app/ test_*.py

build: test lint ## Build the Docker image after running tests
	docker build --target local --tag $(strip $(IMAGE_NAME)):$(strip $(IMAGE_TAG)) .

docker-run: ## Run the app in a Docker container
	docker run --publish $(strip $(PORT)):8000 --env KIOSK_DWELL_SECONDS=$(strip $(KIOSK_DWELL_SECONDS)) --rm $(strip $(IMAGE_NAME)):$(strip $(IMAGE_TAG))
