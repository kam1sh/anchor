import functools
import logging
import xmlrpc.server
from xmlrpc.client import Fault

from django import http
from django.db.models import Q
from django.views.decorators import csrf

from .. import models

log = logging.getLogger(__name__)


__all__ = ["dispatch"]


class _Dispatcher:
    def search(self, spec: dict, operator="and"):
        if not all(x in {"name", "summary"} for x in spec):
            raise ValueError("Function supports only 'name' and 'summary' fields")

        query_spec = [Q(**{f"{key}__contains": val[0]}) for key, val in spec.items()]

        params = functools.reduce(
            lambda x, y: getattr(x, f"__{operator}__")(y), query_spec
        )
        log.debug("Query parameters: %s", params)

        query = models.PythonPackage.objects.filter(params)
        return [
            dict(name=x.name, version=x.version, summary=x.summary) for x in query[:100]
        ]


@csrf.csrf_exempt
def dispatch(request):
    dispatcher = _Dispatcher()
    body = request.body
    params, methodname = xmlrpc.server.loads(data=body)
    log.debug("%s params: %s", methodname, params)
    f = getattr(dispatcher, methodname, None)
    if f:
        try:
            response = (f(*params),)
        except ValueError as e:
            response = Fault(400, str(e))
    else:
        response = Fault(405, "Function not found")
    return http.HttpResponse(xmlrpc.server.dumps(response, allow_none=True), "text/xml")
