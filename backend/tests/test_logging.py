"""Structured (JSON) logging and request-id propagation into log records."""

import json
import logging
import sys

from django.http import HttpResponse
from django.test import RequestFactory

from apps.common.observability import JSONFormatter, RequestIDFilter, RequestIDMiddleware


def _record(**kwargs):
    defaults = {
        "name": "nexus.test",
        "level": logging.INFO,
        "pathname": __file__,
        "lineno": 1,
        "msg": "hello %s",
        "args": ("world",),
        "exc_info": None,
    }
    return logging.LogRecord(**{**defaults, **kwargs})


def test_json_formatter_emits_the_core_fields():
    payload = json.loads(JSONFormatter().format(_record()))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "nexus.test"
    assert payload["message"] == "hello world"
    assert "timestamp" in payload
    # request_id is omitted (not null/"-") when there is no request context.
    assert "request_id" not in payload


def test_json_formatter_includes_request_id_when_the_filter_set_it():
    record = _record()
    record.request_id = "abc123"

    payload = json.loads(JSONFormatter().format(record))
    assert payload["request_id"] == "abc123"


def test_json_formatter_renders_exceptions_without_a_raw_traceback_field():
    try:
        raise ValueError("boom")
    except ValueError:
        record = _record(exc_info=sys.exc_info())

    payload = json.loads(JSONFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]


def test_json_formatter_adds_http_context_but_never_headers_or_cookies():
    request = RequestFactory().get(
        "/api/v1/orders/?token=leaky",
        HTTP_AUTHORIZATION="Bearer super-secret-jwt",
        HTTP_COOKIE="sessionid=secret; refresh=secret",
    )
    record = _record(name="django.request", msg="Internal Server Error: /api/v1/orders/", args=())
    record.request = request
    record.status_code = 500

    text = JSONFormatter().format(record)
    payload = json.loads(text)

    assert payload["method"] == "GET"
    assert payload["path"] == "/api/v1/orders/"  # no query string
    assert payload["status"] == 500
    assert "super-secret-jwt" not in text
    assert "sessionid" not in text
    assert "token=leaky" not in text


def test_request_id_filter_falls_back_to_a_placeholder_outside_a_request():
    record = _record()
    RequestIDFilter().filter(record)
    assert record.request_id == "-"


def test_request_id_from_middleware_is_visible_to_a_log_filter_during_the_request():
    seen = {}

    def view(request):
        record = _record()
        RequestIDFilter().filter(record)
        seen["request_id"] = record.request_id
        return HttpResponse()

    RequestIDMiddleware(view)(RequestFactory().get("/", HTTP_X_REQUEST_ID="flow-1"))
    assert seen["request_id"] == "flow-1"


def test_logging_config_registers_the_json_formatter_and_request_id_filter(settings):
    assert "json" in settings.LOGGING["formatters"]
    assert "request_id" in settings.LOGGING["filters"]
    assert "request_id" in settings.LOGGING["handlers"]["console"]["filters"]
