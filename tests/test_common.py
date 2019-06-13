import json
import logging
from dataclasses import dataclass
from unittest import TestCase

import pytest
from anchor import exceptions
from anchor.common import debug, middleware, views
from anchor.common.middleware import RequestBinder
from django.http.request import QueryDict
from pytest import mark

from . import basic_auth


@pytest.fixture(autouse=True)
def logger(caplog):
    caplog.set_level("DEBUG", "anchor.common.middleware")


@mark.unit
def test_logger(requests):
    logger = debug.Logger("test_logger")
    logger.debug([1, 2, 3])
    req = requests.get()
    logger.dump_headers(req)
    # caplog.text / records


@mark.unit
def test_exception_response():
    exc = exceptions.UserError("Invalid username")
    response = exc.to_response()
    assert exc.status_code == response.status_code
    assert str(exc) == response.content.decode()


def test_auth(users, requests, client):
    users.new("test2@localhost", login="test2")
    user = dict(login="test2@localhost", password="123")
    value = "Basic: dGVzdDJAbG9jYWxob3N0OjEyMw=="

    assert basic_auth(**user) == value
    dct = {}  # type: ignore
    basic_auth(request=dct, **user)
    assert dct.get("HTTP_AUTHORIZATION") == value
    req = requests.get()
    basic_auth(request=req, **user)
    assert "HTTP_AUTHORIZATION" in req.META


@mark.unit
def test_serialize_response(requests):
    def view(request):
        return {"items": []}

    req = requests.get()
    mw = middleware.ExtraMiddleware(view)
    response = mw(req).content
    print(response)
    assert json.loads(response)


@dataclass
class DataClass:
    number: int
    data: str


def do_bind(request, target=DataClass):
    return RequestBinder(request).bind_callable(target)


data = dict(number=1, data="abc")


@mark.unit
def test_process_dataclass(requests):
    req = requests.get(data=data)
    assert do_bind(req) == data
    incomplete = requests.get(data={"number": 1})
    with pytest.raises(exceptions.UserError):
        do_bind(incomplete)
    exceeds = requests.get(data=dict(**data, new="123"))

    error = "Binder did not drop unused values"
    assert do_bind(exceeds) == data, error


@mark.unit
def test_get_view(requests):
    def view(request, page: int, size: int = 4):
        assert page == 3 and size == 4

    req = requests.get(data=dict(page=3, size=4))
    RequestBinder(req).bind_view(view)


def test_dataclass_middleware(requests):
    def view(request, post: DataClass):
        assert isinstance(post, DataClass)
        assert post.number == 1 and post.data == "abc"
        return True

    req = requests.post(data=data)
    mw = middleware.ExtraMiddleware()
    assert mw.process_view(req, view, [], {})


def test_middleware_args(requests):
    def view(request, name):
        return {}

    req = requests.get()
    mw = middleware.ExtraMiddleware()
    assert mw.process_view(req, view, [], {"name": "test"}).status_code == 200
