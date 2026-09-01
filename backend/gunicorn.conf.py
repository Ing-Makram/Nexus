"""Gunicorn configuration for NEXUS (production).

Every value is environment-driven with a sensible default. Logs go to
stdout/stderr so the container runtime owns log collection.
"""

import multiprocessing
import os


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    return int(raw) if raw and raw.isdigit() else default


# --- Networking --------------------------------------------------------------
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")

# Trust the reverse proxy's forwarded headers (X-Forwarded-For / -Proto).
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")

# --- Workers ----------------------------------------------------------------
# Default follows Gunicorn's own recommendation: (2 x cores) + 1. Override with
# GUNICORN_WORKERS on constrained hosts.
workers = _int("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1)
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
threads = _int("GUNICORN_THREADS", 1)

# --- Timeouts / lifecycle -------------------------------------------------
timeout = _int("GUNICORN_TIMEOUT", 30)
graceful_timeout = _int("GUNICORN_GRACEFUL_TIMEOUT", 30)
keepalive = _int("GUNICORN_KEEPALIVE", 5)

# Recycle workers periodically to bound memory growth. Jitter avoids a
# thundering-herd restart.
max_requests = _int("GUNICORN_MAX_REQUESTS", 1000)
max_requests_jitter = _int("GUNICORN_MAX_REQUESTS_JITTER", 100)

# --- Logging ----------------------------------------------------------------
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Tie the access log to the correlation ID that nginx / Django propagate via the
# X-Request-ID request header (see apps.common.observability).
access_log_format = os.getenv(
    "GUNICORN_ACCESS_LOG_FORMAT",
    '%(h)s %(l)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" request_id=%({x-request-id}i)s',
)
