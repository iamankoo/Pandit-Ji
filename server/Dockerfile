# Build context is the repository root (see infrastructure/docker-compose.yml)
# because server/ depends on the local path packages packages/contracts,
# packages/shared, and all five domain services (its health.py imports each
# service's get_health()).
#
# Two stages: `builder` has a C compiler (pandit-astro-engine's pyswisseph
# dependency has no prebuilt wheel for every platform/Python combination and
# must build a C extension from source); the final image copies only the
# resulting virtualenv, so gcc never ships in the runtime image.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY packages/contracts /app/packages/contracts
COPY packages/shared /app/packages/shared
COPY services/astro-engine /app/services/astro-engine
COPY services/rule-engine /app/services/rule-engine
COPY services/agent /app/services/agent
COPY services/knowledge /app/services/knowledge
COPY services/verification /app/services/verification
COPY server /app/server

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir \
      /app/packages/contracts \
      /app/packages/shared \
      /app/services/astro-engine \
      /app/services/rule-engine \
      /app/services/agent \
      /app/services/knowledge \
      /app/services/verification \
      /app/server

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

RUN useradd --create-home --uid 1000 pandit
USER pandit

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2)" || exit 1

# Development convenience only: --reload is not used here. Use
# docker-compose.yml's `command:` override for --reload in local dev, so the
# production image itself always runs the plain, non-reload server.
CMD ["uvicorn", "pandit_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
