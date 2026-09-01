#!/usr/bin/env sh
# Production container startup: wait for the database, run migrations and
# collectstatic, then hand off to Gunicorn. Any failure aborts the boot
# (set -e) - failures are never hidden.
set -eu

# This image is production-only. Be explicit rather than relying on ENVIRONMENT.
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
RUN_COLLECTSTATIC="${RUN_COLLECTSTATIC:-true}"

echo "[entrypoint] settings module: ${DJANGO_SETTINGS_MODULE}"

echo "[entrypoint] waiting for database..."
python <<'PY'
import sys
import time

import django
from django.db import connections
from django.db.utils import OperationalError

django.setup()
for attempt in range(1, 61):
    try:
        connections["default"].cursor().execute("SELECT 1")
        print(f"[entrypoint] database ready (attempt {attempt})")
        break
    except OperationalError:
        time.sleep(1)
else:
    sys.exit("[entrypoint] database did not become available within 60s")
PY

if [ "${RUN_MIGRATIONS}" = "true" ]; then
    echo "[entrypoint] applying migrations..."
    python manage.py migrate --noinput
else
    echo "[entrypoint] RUN_MIGRATIONS=false - skipping migrations"
fi

if [ "${RUN_COLLECTSTATIC}" = "true" ]; then
    echo "[entrypoint] collecting static files..."
    python manage.py collectstatic --noinput
else
    echo "[entrypoint] RUN_COLLECTSTATIC=false - skipping collectstatic"
fi

echo "[entrypoint] starting Gunicorn..."
exec gunicorn config.wsgi:application --config gunicorn.conf.py "$@"
