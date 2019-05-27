import json
from dataclasses import dataclass

from anchor.common import middleware, debug
from django.http.request import QueryDict
from django.test import RequestFactory as Requests
from pytest import mark


@mark.unit
def test_logger():
    logger = debug.Logger("test_logger")
    logger.debug([1, 2, 3])
    req = Requests().get("/test")
    logger.dump_headers(req)


@mark.unit
def test_serialize_response():
    def view(request):
        return {"items": []}

    req = Requests().get("/test/")
    mw = middleware.ExtraMiddleware(view)
    response = mw(req).content
    print(response)
    assert json.loads(response)


@mark.unit
def test_process_dataclass():
    @dataclass
    class DataClass:
        number: int

    post = QueryDict("number=1")
    middleware.bind_form(post, DataClass)

    def view(request, post: DataClass):
        assert post
        assert post.number == 1

    req = Requests().post("/test/", data=post)
    mw = middleware.ExtraMiddleware()
    mw.process_view(req, view, [], {})
