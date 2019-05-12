from __future__ import annotations

import functools
import inspect
import logging

from django.http import HttpResponse
from django.http.response import HttpResponseBase

from . import exceptions, helpers

log = logging.getLogger(__name__)


@functools.lru_cache()
def cached_signature(cls):
    return inspect.signature(cls)


def bind_form(data, cls, signature=None):
    """Binds form to the class constructor."""
    signature = signature or cached_signature(cls)
    params = signature.parameters
    log.debug("%s params: %s", cls, params)
    # maybe that function accepts a form?
    if len(params) == 1:
        return cls(data)
    try:
        return cls(**data)
    except TypeError as e:
        raise exceptions.ServiceError("Failed to bind form") from e


class FunctionInfo:
    """
    Various information about function.
    Fields:
      function: function that was passed
      original: original function without decorators
      decorators: list of function decorators
      signature: function signature
    """

    def __init__(self, function):
        self.function = function
        parent = function
        self.decorators = []
        # range(x) instead of `while True:` to avoid infinite loops
        for _ in range(128):
            # functools.wraps puts __wrapped__ attribute at the function
            # that points at the wrapped function
            decorated = getattr(parent, "__wrapped__", None)
            if not decorated:
                break
            self.decorators.append(parent)
            parent = decorated
        self.original = parent

    @classmethod
    @functools.lru_cache()
    def from_cache(cls, function):
        return cls(function)

    @property
    def signature(self) -> inspect.Signature:
        return cached_signature(self.original)

    @property
    def annotations(self) -> dict:
        return self.original.__annotations__

    def __str__(self):
        return self.original.__module__ + "." + self.original.__name__

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self)


class ExtraMiddleware:
    """
    Middleware that automatically serializes response
    and wraps exceptions in HTTP responses
    """

    def __init__(self, get_response=None):
        self._function = get_response

    def __call__(self, request) -> HttpResponse:
        response = self._function(request)
        # checking for HttpResponseBase instead of HttpResponse
        # because FileResponse is derived from HttpResponseBase =/
        if not isinstance(response, HttpResponseBase):
            response = helpers.jsonify(response)
        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        orig_view = FunctionInfo.from_cache(view_func)
        if "post" in orig_view.signature.parameters:
            view_kwargs["post"] = bind_form(
                request.POST,
                orig_view.annotations["post"],
                signature=orig_view.signature,
            )
        log.debug("Processing view %s", orig_view)
        return view_func(request, *view_args, **view_kwargs)

    def process_exception(self, request, exception):
        if isinstance(exception, exceptions.ServiceError):
            return HttpResponse(str(exception), status=exception.status_code)
