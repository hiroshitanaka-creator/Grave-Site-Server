FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md requirements.lock ./
COPY src/ ./src/
RUN pip install --no-cache-dir -c requirements.lock ".[google,cloud]" \
    && useradd --uid 10001 --create-home appuser \
    && mkdir -p /app/data && chown appuser:appuser /app/data
USER appuser
EXPOSE 8080
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
