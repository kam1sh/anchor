from __future__ import annotations

import functools
import inspect
import logging
import typing as ty

from django.http import HttpResponse, QueryDict
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
    - function: function that was passed
    - original: original function without decorators
    - decorators: list of function decorators
    - signature: function signature
    - annotations: dict of function annotations
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
    Class that can bind request data to the various classes, function params etc.
    """

    def __init__(self, request, existing_kwargs=None):
        self.request = request
        self.kwargs = existing_kwargs or {}

    def bind_view(self, view: ty.Callable) -> dict:
        """Binds request to the view function"""
        info = FunctionInfo(view)
        return self._bind(info)

    def _bind(self, info: FunctionInfo) -> dict:
        out = {}
        params = info.signature.parameters
        if "post" in params:
            # we've got the POST view, so we have to extract post annotation
            # and look at her signature
            cls = params["post"].annotation
            cls_args = self.bind_callable(cls)
            out["post"] = cls(**cls_args)
        else:
            out = self.bind_params(params, exclude={"request"})
        return out

    def bind_callable(self, func: ty.Callable, exclude: ty.Container = None) -> dict:
        params = cached_signature(func).parameters
        return self.bind_params(params, exclude=exclude)

    def bind_params(self, params: ty.Mapping, exclude: ty.Container = None) -> dict:
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


def iter_params(
    items: QueryDict, params: ty.Mapping[str, ty.Any], exclude: ty.Container[str] = None
) -> ty.Iterator[ty.Tuple[str, inspect.Parameter, ty.Any]]:
    """
    Yields field name, field type annotation and the items[value].
    Accepts:

    """
    exclude = exclude or set()
    for field, field_type in params.items():
        if field in exclude:
            continue
        value = items.getlist(field)
        yield (field, field_type, value)


def convert_arg(arg: ty.List[str], val_type: ty.Type):
    if val_type in {str, "str"}:
        return arg[0]
    if issubclass(val_type, ty.Iterable):
        return arg
    return val_type(arg[0])
