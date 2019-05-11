from django.http import HttpResponse
from django.http.response import HttpResponseBase

from . import exceptions, helpers


class ExtraMiddleware:
    """
    Middleware that automatically serializes response
    and wraps exceptions in HTTP responses
    """

    def __init__(self, get_response):
        self._function = get_response

    def __call__(self, request) -> HttpResponse:
        response = self._function(request)
        # checking for HttpResponseBase instead of HttpResponse
        # because FileResponse is derived from HttpResponseBase =/
        if not isinstance(response, HttpResponseBase):
            response = helpers.jsonify(response)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, exceptions.ServiceError):
            return HttpResponse(str(exception), status=exception.status_code)
