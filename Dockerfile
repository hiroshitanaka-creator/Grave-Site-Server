FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY src/ ./src/
COPY prompts/ ./prompts/
COPY pyproject.toml README.md ./

ENTRYPOINT ["python", "src/openai_diary_batch.py"]
CMD ["--help"]
