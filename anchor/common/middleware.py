from __future__ import annotations

import dataclasses
import functools
import inspect
import logging
import typing as ty

from django.http import HttpResponse
from django.http.response import HttpResponseBase

from . import exceptions, helpers

log = logging.getLogger(__name__)


@functools.lru_cache()
def cached_signature(cls):
    # https://docs.python.org/3/library/inspect.html#inspect.Signature
    return inspect.signature(cls)


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
        sig = orig_view.signature
        if "post" in sig.parameters:
            view_kwargs["post"] = bind_form(request.POST, orig_view.annotations["post"])
        log.debug("Processing view %s", orig_view)
        # exceptions from process_view sometimes are not handled (???)
        # for example, in test_pypi::test_upload_permission
        try:
            return view_func(request, *view_args, **view_kwargs)
        except exceptions.ServiceError as exception:
            return HttpResponse(str(exception), status=exception.status_code)

    def process_exception(self, request, exception):
        if isinstance(exception, exceptions.ServiceError):
            return HttpResponse(str(exception), status=exception.status_code)


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


def bind_form(data: dict, cls, signature: inspect.Signature = None):
    """
    Binds form to the class constructor.
    """
    signature = signature or cached_signature(cls)
    params = signature.parameters
    log.debug("sig: %r, params: %s", signature, params)

    kwargs = {}
    # required_params = params
    for key, param in params.items():
        if key == "request":
            continue
        annotation = param.annotation
        val = getval(data, key)
        kwargs[key] = convert_arg(val, annotation)
    if dataclasses.is_dataclass(cls):
        return cls(**kwargs)
    raise exceptions.ServiceError("Failed to bind form")


def getval(data, key):
    if hasattr(data, "getlist"):
        return data.getlist(key)
    return data[key]


def convert_arg(arg: ty.List[str], val_type: type):
    # check in case of tests that passes usual dicts
    if not isinstance(arg, list):
        arg = [arg]
    if val_type in {str, "str"}:
        return arg[0]
    if val_type in [ty.Iterable]:
        return [val_type(x) for x in arg]
    return val_type(arg[0])
