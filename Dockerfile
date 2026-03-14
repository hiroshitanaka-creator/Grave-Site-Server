FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY src/ ./src/
COPY prompts/ ./prompts/
COPY pyproject.toml README.md ./

RUN pip install --no-cache-dir fastapi "uvicorn[standard]" pydantic

# デフォルト: API サーバーを起動
# バッチ実行: docker run ... python src/llm_batch.py --help
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
