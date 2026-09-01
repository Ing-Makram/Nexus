# syntax=docker/dockerfile:1
# ==============================================================================
# NEXUS backend - production image
# Runs Django under Gunicorn. Never runs the development server.
# Build context: the backend/ directory.
# ==============================================================================
FROM python:3.12-slim AS runtime

# - PYTHONDONTWRITEBYTECODE: no .pyc files in the image
# - PYTHONUNBUFFERED: stream logs straight to stdout/stderr
# - PIP_NO_CACHE_DIR: smaller image
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# psycopg2-binary ships its own libpq, so no build toolchain or libpq-dev is
# needed. tini gives us correct signal handling / zombie reaping for Gunicorn.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Dependencies first for layer caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Application code.
COPY . .

RUN chmod +x docker-entrypoint.sh \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app \
    && mkdir -p /app/staticfiles \
    && chown -R app:app /app

USER app

EXPOSE 8000

ENTRYPOINT ["/usr/bin/tini", "--", "/app/docker-entrypoint.sh"]
