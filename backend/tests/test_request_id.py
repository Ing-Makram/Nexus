"""RequestIDMiddleware: inbound preservation, generation, response header."""

import re

from django.http import HttpResponse
from django.test import Client, RequestFactory

from apps.common.observability import RequestIDMiddleware, get_request_id

HEX32 = re.compile(r"\A[0-9a-f]{32}\Z")


def test_generated_request_id_is_returned_when_none_supplied():
    response = Client().get("/health/")

    request_id = response.headers.get("X-Request-ID")
    assert request_id, "response must carry an X-Request-ID header"
    assert HEX32.match(request_id), f"generated id should be 32 hex chars, got {request_id!r}"


def test_supplied_request_id_is_preserved():
    response = Client().get("/health/", HTTP_X_REQUEST_ID="trace-abc_123.4")

    assert response.headers.get("X-Request-ID") == "trace-abc_123.4"


def test_malformed_request_id_is_replaced_with_a_generated_one():
    supplied = "not a valid id — spaces & unicode\nnewline"
    response = Client().get("/health/", HTTP_X_REQUEST_ID=supplied)

    request_id = response.headers.get("X-Request-ID")
    assert request_id != supplied
    assert HEX32.match(request_id)


def test_overlong_request_id_is_rejected():
    response = Client().get("/health/", HTTP_X_REQUEST_ID="a" * 500)

    assert HEX32.match(response.headers.get("X-Request-ID"))


def test_middleware_sets_request_attr_and_contextvar_then_clears_it():
    seen = {}

    def view(request):
        seen["attr"] = request.request_id
        seen["contextvar"] = get_request_id()
        return HttpResponse()

    request = RequestFactory().get("/", HTTP_X_REQUEST_ID="ctx-check-9")
    response = RequestIDMiddleware(view)(request)

    assert seen["attr"] == "ctx-check-9"
    assert seen["contextvar"] == "ctx-check-9"
    assert response["X-Request-ID"] == "ctx-check-9"
    # Context var must not leak past the request.
    assert get_request_id() is None
