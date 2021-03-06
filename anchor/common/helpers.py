import dataclasses
import functools
import json

from django.db import models
from django.db.models.query import QuerySet
from django.http import HttpResponse


class JsonResponse(HttpResponse):
    def __init__(self, data, **kwargs):
        content_type = "application/json"
        super().__init__(json.dumps(data), content_type=content_type, **kwargs)


serializable = (dict, list, tuple, str, int, float, bool, type(None))


@functools.singledispatch
def jsonify(data=None, **kwargs) -> JsonResponse:
    """
    Serializes any data (dict, django model, Paginator, QuerySet etc)
    to HttpResponse.
    """
    data = data or kwargs
    if not isinstance(data, dict):
        data = dict(items=data)
    return JsonResponse(data)


@jsonify.register(models.Model)
def _(data: models.Model = None, **kwargs):
    fields = _process_kwargs(data._meta, kwargs)
    return JsonResponse(_model_to_dict(data, fields))


@jsonify.register(QuerySet)  # type: ignore
def _(data: QuerySet = None, **kwargs):
    fields = _process_kwargs(data.model._meta, kwargs)
    # TODO use .values()?
    items = [_model_to_dict(x, fields) for x in data]
    return JsonResponse(dict(items=items))


def _model_to_dict(mdl, fields):
    return {
        k: v
        for k, v in ((field, getattr(mdl, field)) for field in fields)
        if isinstance(v, serializable)
    }


def _process_kwargs(meta, kwargs: dict) -> set:
    fields = {x.name for x in meta.get_fields()}
    include = kwargs.get("include")
    exclude = kwargs.get("exclude")
    if include:
        fields = fields | set(include)
    if exclude:
        fields = fields ^ set(exclude)
    return fields


class DataclassExtras:
    @classmethod
    def from_dict(cls, data):
        kwargs = {}
        for field in dataclasses.fields(cls):
            name = field.name
            kwargs[name] = data[name]
        return cls(**kwargs)
