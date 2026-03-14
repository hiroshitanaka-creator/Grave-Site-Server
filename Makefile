.PHONY: setup run test lint format clean deploy-cloudrun

PYTHON ?= python3
VENV ?= .venv

setup:
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install --upgrade pip

	run:
	@if [ ! -f input.txt ]; then \
		echo "input.txt が見つかりません。1行1日記で input.txt を作成してから再実行してください。"; \
		exit 1; \
	fi
	$(PYTHON) src/diary_cli.py --input input.txt --format json

test:
	@if [ -d tests ]; then \
		if $(PYTHON) -c "import pytest" >/dev/null 2>&1; then \
			$(PYTHON) -m pytest -q; \
		else \
			echo "pytest が未インストールのため、構文チェックにフォールバックします"; \
			files="$$(find . -name '*.py' -not -path './.venv/*')"; \
			if [ -n "$$files" ]; then \
				$(PYTHON) -m py_compile $$files; \
			else \
				echo "対象の Python ファイルがないため、構文チェックをスキップします"; \
			fi; \
		fi; \
	else \
		echo "tests/ が存在しないため、構文チェックにフォールバックします"; \
		files="$$(find . -name '*.py' -not -path './.venv/*')"; \
		if [ -n "$$files" ]; then \
			$(PYTHON) -m py_compile $$files; \
		else \
			echo "対象の Python ファイルがないため、構文チェックをスキップします"; \
		fi; \
	fi

lint:
	@if command -v ruff >/dev/null 2>&1; then \
		ruff check . ; \
	else \
		echo "ruff が未インストールのため lint をスキップします"; \
	fi

format:
	@if command -v ruff >/dev/null 2>&1; then \
		ruff format . ; \
	else \
		echo "ruff が未インストールのため format をスキップします"; \
	fi

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .venv


CLOUD_RUN_REGION ?= asia-northeast1
CLOUD_RUN_SERVICE ?= grave-site-batch
GCP_PROJECT_ID ?= your-gcp-project-id
IMAGE_URI ?= $(CLOUD_RUN_REGION)-docker.pkg.dev/$(GCP_PROJECT_ID)/grave-site/grave-site-batch:latest

deploy-cloudrun:
	gcloud run deploy $(CLOUD_RUN_SERVICE) \
		--project $(GCP_PROJECT_ID) \
		--region $(CLOUD_RUN_REGION) \
		--image $(IMAGE_URI) \
		--platform managed \
		--allow-unauthenticated \
		--min-instances 0 \
		--max-instances 2 \
		--cpu 1 \
		--memory 512Mi \
		--timeout 300
