.PHONY: setup run test lint format clean

PYTHON ?= python3
VENV ?= .venv

setup:
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install --upgrade pip

run:
	@echo "MVPはCLI実装前のため、READMEのテンプレを参照してください。"

# 現状のドキュメントリポジトリ向けの最小チェック
test:
	@files="$$(find . -name '*.py' -not -path './.venv/*')"; \
	if [ -n "$$files" ]; then \
		$(PYTHON) -m py_compile $$files; \
	else \
		echo "対象の Python ファイルがないため、構文チェックをスキップします"; \
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
