"""Infrastructure-level observability helpers (no business logic).

Provides:

* a request/correlation ID that flows client -> nginx -> Gunicorn -> Django
  -> logs, exposed on the response as ``X-Request-ID``;
* a logging filter that injects that ID into every log record;
* a JSON log formatter for production (machine-readable, secret-free).

Nothing here logs headers, cookies, request bodies, or credentials.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime

REQUEST_ID_HEADER = "X-Request-ID"

# Accept an inbound ID only if it is short and unsurprising: this value ends up
# in logs and response headers, so it must not carry newlines or control chars.
_VALID_REQUEST_ID = re.compile(r"\A[A-Za-z0-9._-]{1,128}\Z")

_request_id: ContextVar[str | None] = ContextVar("nexus_request_id", default=None)


def get_request_id() -> str | None:
    """The current request's ID, or ``None`` outside a request."""
    return _request_id.get()


def generate_request_id() -> str:
    return uuid.uuid4().hex


def sanitize_request_id(value: str | None) -> str | None:
    """Return ``value`` if it is a safe, well-formed ID, else ``None``."""
    if value and _VALID_REQUEST_ID.match(value):
        return value
    return None


class RequestIDMiddleware:
    """Preserve an inbound ``X-Request-ID`` (if valid) or mint a new one.

    Puts the ID on ``request.request_id``, in a context var for logging, and on
    the response header.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = (
            sanitize_request_id(request.headers.get(REQUEST_ID_HEADER)) or generate_request_id()
        )
        request.request_id = request_id
        token = _request_id.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            _request_id.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response


class RequestIDFilter(logging.Filter):
    """Make ``%(request_id)s`` available to every handler/formatter."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "request_id", None):
            record.request_id = get_request_id() or "-"
        return True


class JSONFormatter(logging.Formatter):
    """One JSON object per line: timestamp, level, logger, message, request_id.

    For records emitted by ``django.request`` it also includes method/path/status.
    It never serialises headers, cookies, or the request body.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None)
        if request_id and request_id != "-":
            payload["request_id"] = request_id

        request = getattr(record, "request", None)
        if request is not None:
            method = getattr(request, "method", None)
            path = getattr(request, "path", None)  # never get_full_path(): no query string
            if method:
                payload["method"] = method
            if path:
                payload["path"] = path
        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            payload["status"] = status_code

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)
