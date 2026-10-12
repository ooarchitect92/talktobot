# syntax=docker/dockerfile:1.7
FROM ghcr.io/astral-sh/uv:0.9.30@sha256:538e0b39736e7feae937a65983e49d2ab75e1559d35041f9878b7b7e51de91e4 AS uv
FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4 AS builder
COPY --from=uv /uv /uvx /usr/local/bin/
RUN apk add --no-cache build-base zlib-dev

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY migrations ./migrations
COPY help_content ./help_content
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM python:3.12-alpine@sha256:1b668429b3511ab407d8e00648891631b0b1a4d7e15e3ca70f38ab5b91ad4ab4 AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000
RUN apk upgrade --no-cache \
    && apk add --no-cache libreoffice-writer fontconfig font-dejavu font-noto font-noto-cjk tesseract-ocr tesseract-ocr-data-eng \
    && addgroup -S -g 10001 app \
    && adduser -S -D -u 10001 -G app -h /app app
WORKDIR /app
COPY rds-ca-bundle.crt /etc/northstar/rds-ca-bundle.crt
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --from=builder --chown=app:app /app/src /app/src
COPY --from=builder --chown=app:app /app/migrations /app/migrations
COPY --from=builder --chown=app:app /app/help_content /app/help_content
COPY --from=builder --chown=app:app /app/alembic.ini /app/alembic.ini
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/live', timeout=3)"
CMD ["uvicorn", "northstar_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
