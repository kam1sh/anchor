from __future__ import annotations

import dataclasses
import functools
import inspect
import logging
import typing as ty

from django.http import HttpResponse
from django.http.response import HttpResponseBase

from .. import exceptions
from . import helpers

log = logging.getLogger(__name__)


@functools.lru_cache()
def cached_signature(cls) -> inspect.Signature:
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
        return self._wrap_json(response)

    def process_view(self, request, view_func, view_args, view_kwargs) -> HttpResponse:
        binder = RequestBinder(request, existing_kwargs=view_kwargs)
        try:
            kwargs = binder.bind_view(view_func)
            view_kwargs.update(kwargs)
            response = view_func(request, *view_args, **view_kwargs)
            return self._wrap_json(response)
        # exceptions from process_view are not handled by process_exception (???)
        except exceptions.ServiceError as exception:
            return exception.to_response()

    def _wrap_json(self, response) -> HttpResponse:
        if not isinstance(response, HttpResponseBase):
            response = helpers.jsonify(response)
        # checking for HttpResponseBase instead of HttpResponse
        # because FileResponse is derived from HttpResponseBase =/
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, exceptions.ServiceError):
            return exception.to_response()


class FunctionInfo:
    """
    Various information about function.
    Fields:
      function: function that was passed
      original: original function without decorators
      decorators: list of function decorators
      signature: function signature
      annotations: dict of function annotations
    """

    def __init__(self, function):
        self.function = function
        parent = function
        self.decorators = []  # type: ignore
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


class RequestBinder:
    """
    Class that can bind request info to the various classes.
    """

    def __init__(self, request, existing_kwargs=None):
        self.request = request
        self.kwargs = existing_kwargs or {}

    def bind_view(self, view) -> dict:
        info = FunctionInfo(view)
        return self._bind(info)

    def _bind(self, info: FunctionInfo) -> dict:
        """ Binds request to the parameters. """
        out = {}
        params = info.signature.parameters
        if "post" in params:
            cls = params["post"].annotation
            cls_args = self.bind_callable(cls, exclude={"request", "post"})
            out["post"] = cls(**cls_args)
        else:
            out = self.bind_params(params, exclude={"request"})
        return out

    def bind_get(self, params) -> dict:
        out = {}
        items = self.request.GET
        for field, field_type, value in iter_params(items, params, exclude={"request"}):
            if not isinstance(value, field_type):
                raise exceptions.UserError(
                    f"Parameter type of {field} mismatch: expected {field_type.__name__}"
                )
            out[field] = value
        return out

    def bind_callable(self, func: ty.Callable, exclude=None) -> dict:
        params = cached_signature(func).parameters
        return self.bind_params(params, exclude=exclude)

    def bind_params(self, params: ty.Mapping, exclude=None) -> dict:
        """ Binds request to the provided params."""
        exclude = exclude or set()
        out = {}
        items = self.request.GET or self.request.POST
        for field, field_type, value in iter_params(items, params, exclude=exclude):
            if field in self.kwargs:
                # field already provided by another middleware
                continue
            try:
                out[field] = convert_arg(value, field_type.annotation)
            except IndexError:  # empty list - no param provided
                raise exceptions.UserError(
                    f"Parameter {field!r} not provided"
                ) from None
        return out


def bind_form(data: dict, cls=None, exclude=None):
    """
    Binds form to the class constructor.
    """
    params = FunctionInfo.from_cache(cls).signature.parameters
    kwargs = {}
    for key, param in params.items():
        annotation = param.annotation
        val = getval(data, key)
        try:
            kwargs[key] = convert_arg(val, annotation)
        except IndexError:  # empty list - no param provided
            raise exceptions.UserError(f"Parameter {key} not provided") from None
    if cls:
        if dataclasses.is_dataclass(cls):
            return cls(**kwargs)
    return kwargs


def iter_params(items: dict, params: ty.Mapping, exclude=None):
    exclude = exclude or set()
    for field, field_type in params.items():
        if field in exclude:
            continue
        value = getval(items, field)
        yield (field, field_type, value)


def getval(data, key):
    if hasattr(data, "getlist"):
        return data.getlist(key)
    return data[key]


def convert_arg(arg: ty.List[str], val_type: type):
    # check in case of tests that passes usual dicts
    if not isinstance(arg, list):
        arg = [arg]  # type: ignore
    if val_type in {str, "str"}:
        return arg[0]
    if val_type in [ty.Iterable]:
        return [val_type(x) for x in arg]
    return val_type(arg[0])
