import json
from dataclasses import dataclass

import pytest
from django.http.request import QueryDict
from django.test import RequestFactory as Requests

from anchor.common import middleware


def test_serialize_response():
    def view(request):
        return {"items": []}

    req = Requests().get("/test/")
    mw = middleware.ExtraMiddleware(view)
    response = mw(req).content
    print(response)
    assert json.loads(response)


@pytest.mark.skip("Dataclasses is not supported yet.")
def test_process_dataclass():
    @dataclass
    class DataClass:
        number: int

    def view(request, post: DataClass):
        assert post
        assert post.number == 1

    data = QueryDict("number=1")
    req = Requests().post("/test/", data=data)
    mw = middleware.ExtraMiddleware()
    mw.process_view(req, view, [], {})
