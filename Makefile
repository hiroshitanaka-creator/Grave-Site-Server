.PHONY: setup run serve test lint format build schema dry-run clean deploy-cloudrun
PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

setup:
	$(PYTHON) -m venv $(VENV)
	$(BIN)/python -m pip install -c requirements.lock -e ".[dev,google,cloud]"

run:
	$(BIN)/grave-diary --input input.txt --format json

serve:
	$(BIN)/uvicorn src.api.main:app --host 127.0.0.1 --port 8080

test:
	$(BIN)/python -m pytest

lint:
	$(BIN)/ruff check .

format:
	$(BIN)/ruff format .

build:
	$(BIN)/python -m build

schema:
	$(BIN)/grave-openapi

dry-run:
	$(BIN)/grave-deliver --dry-run

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .venv

# Reviewed configuration is now mandatory: image-only deployments lack a durable store.
CLOUD_RUN_REGION ?= asia-northeast1
SERVICE_CONFIG ?= deploy/cloudrun-service.yaml
deploy-cloudrun:
	test -n "$(GCP_PROJECT_ID)"
	$(BIN)/python -c 'from pathlib import Path; import sys; assert "REPLACE_" not in Path(sys.argv[1]).read_text(), "Fill and review all configuration placeholders first"' "$(SERVICE_CONFIG)"
	gcloud run services replace "$(SERVICE_CONFIG)" --project "$(GCP_PROJECT_ID)" --region "$(CLOUD_RUN_REGION)"
