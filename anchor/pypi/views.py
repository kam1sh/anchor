# Python package index API views.

import functools
import logging
import re
import typing as ty
import xmlrpc.server
from xmlrpc.client import Fault

from django import http
from django.db import models
from django.http import HttpResponseBadRequest as badrequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators import csrf

from ..common.views import basic_auth
from ..exceptions import UserError, Forbidden
from . import services
from .models import Metadata, PackageFile, Project

log = logging.getLogger(__name__)


__all__ = [
    "upload_package",
    "list_projects",
    "list_files",
    "download_file",
    "xmlrpc_dispatch",
    "search",
]


allowed_files = re.compile(r".+\.(tar\.gz|zip|whl|egg)$", re.I)


@csrf.csrf_exempt
@basic_auth
def upload_package(request, post: Metadata):
    """
    Uploads new package to the server.
    If package with this filename already exists, it will be updated.

    A few moments:

    - Allowed only sdist and wheel (.tar.gz and .whl)
    - Package name should not conflict with the Python standard library.
    - Package name and version will be normalized if needed.
    """
    raw_file = request.FILES.get("content")
    if not raw_file:
        return badrequest('Provide package within "content" file.')
    services.upload_file(request.user, post, raw_file)
    return http.HttpResponse("Package uploaded succesfully")


def list_projects(request):
    """ Returns page with list of all available projects. """
    return render(request, "projects.html", {"projects": Project.objects.all()})


def list_files(request, name: str):
    """ Returns page with list of all existing files for the package. """
    result = PackageFile.objects.filter(package__name=name)
    return render(
        request, "files.html", dict(title=f"{name.capitalize()} files", files=result)
    )


def download_file(request, filename: str):
    pkg_file = get_object_or_404(PackageFile, filename=filename)
    if not pkg_file.package.has_permission(request.user, "read"):
        raise Forbidden
    pkg_file.package.downloads += 1
    pkg_file.package.save()
    return http.FileResponse(pkg_file.fileobj)


@csrf.csrf_exempt
def xmlrpc_dispatch(request):
    """
    Dispatcher for any `XML RPC`_ methods.
    Currently supports only `search(spec[, operator="and"])`,
    that is used by ``pip search``.

    .. _`XML RPC`: https://docs.python.org/3/library/xmlrpc.html
    """
    body = request.body
    params, methodname = xmlrpc.server.loads(data=body)
    log.debug("%s params: %s", methodname, params)
    if methodname == "search":
        try:
            response = tuple(search(*params))
        except UserError as e:
            response = Fault(400, str(e))
    else:
        response = Fault(405, "Function not found")
    return http.HttpResponse(xmlrpc.server.dumps(response, allow_none=True), "text/xml")


def search(spec: ty.Mapping[str, ty.List[str]], operator: str = "and"):
    """
    Searches for the available packages.

    Arguments:

    - *spec*: fields and lists of values for search.
    - *operator*: string with the operator for combination of specifications.

    Example:

    >>> search({'name': ['foo'], 'summary': ['foo']}, 'or')
    # -> all packages that name or summary contains 'foo'

    Returns list of dicts with fields *name*, *version* and *summary*.
    Warehouse implementation returns at most 100 packages, so did we.
    """
    if not all(x in {"name", "summary"} for x in spec):
        raise UserError("Function supports only 'name' and 'summary' fields")

    query_spec = [models.Q(**{f"{key}__contains": val[0]}) for key, val in spec.items()]

    params = functools.reduce(lambda x, y: getattr(x, f"__{operator}__")(y), query_spec)
    log.debug("Query parameters: %s", params)

    query = Project.objects.filter(params)
    return [
        dict(name=x.name, version=x.version, summary=x.summary) for x in query[:100]
    ]
