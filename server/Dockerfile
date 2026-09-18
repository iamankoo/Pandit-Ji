# Build context is the repository root (see infrastructure/docker-compose.yml)
# because server/ depends on the local path packages packages/contracts and
# packages/shared.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY packages/contracts /app/packages/contracts
COPY packages/shared /app/packages/shared
COPY server /app/server

RUN pip install --no-cache-dir \
      /app/packages/contracts \
      /app/packages/shared \
      /app/server

RUN useradd --create-home --uid 1000 pandit
USER pandit

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

# Development convenience only: --reload is not used here. Use
# docker-compose.yml's `command:` override for --reload in local dev, so the
# production image itself always runs the plain, non-reload server.
CMD ["uvicorn", "pandit_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
