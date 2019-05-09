import functools
import logging
import re
import xmlrpc.server
from xmlrpc.client import Fault

from django import http
from django.db import models, transaction
from django.http import HttpResponseBadRequest as badrequest
from django.shortcuts import render
from django.views.decorators import csrf

from ..common.views import wrap_exceptions, basic_auth
from .models import PackageFile, Project

log = logging.getLogger(__name__)


__all__ = [
    "upload_package",
    "list_projects",
    "list_files",
    "download_file",
    "xmlrpc_dispatch",
]


allowed_files = re.compile(r".+\.(tar\.gz|zip|whl|egg)$", re.I)


@csrf.csrf_exempt
@wrap_exceptions
@basic_auth
def upload_package(request):
    """
    Uploads new package to the server.
    If package with this filename already exists, it will be updated.
    """
    # cl = request.META["CONTENT_LENGTH"] # could be useful in the future
    form = request.POST
    proj_name = form["name"]

    # at first find the project to check permissions
    try:
        project = Project.objects.get(name=proj_name)
        # TODO check permissions
    except Project.DoesNotExist:
        # automatically create new project
        project = Project(name=proj_name)
    project.update_version(form["version"])
    project.update_time()

    # and then the file stuff
    raw_file = request.FILES.get("content")
    if not raw_file:
        return badrequest('Provide package within "content" file.')
    # TODO check file size
    try:
        pkg_file = PackageFile.objects.get(filename=raw_file.name)
        pkg_file.update(raw_file)
    except PackageFile.DoesNotExist:
        pkg_file = PackageFile(pkg=raw_file)

    if pkg_file.sha256 != form["sha256_digest"]:
        return badrequest("Hashsums does not match")

    log.debug("Got package %s and project %s", pkg_file, project)

    with transaction.atomic():
        project.save()
        pkg_file.package = project
        pkg_file.save()
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
    pkg_file = PackageFile.objects.get(filename=filename)
    # pkg = pkg_file.package
    # if not pkg.available_for(current_user):
    #     return http.HttpResponseForbidden()
    return http.FileResponse(pkg_file.fileobj)


@csrf.csrf_exempt
def xmlrpc_dispatch(request):
    body = request.body
    params, methodname = xmlrpc.server.loads(data=body)
    log.debug("%s params: %s", methodname, params)
    if methodname == "search":
        try:
            response = (_search(*params),)
        except ValueError as e:
            response = Fault(400, str(e))
    else:
        response = Fault(405, "Function not found")
    return http.HttpResponse(xmlrpc.server.dumps(response, allow_none=True), "text/xml")


def _search(spec: dict, operator="and"):
    if not all(x in {"name", "summary"} for x in spec):
        raise ValueError("Function supports only 'name' and 'summary' fields")

    query_spec = [models.Q(**{f"{key}__contains": val[0]}) for key, val in spec.items()]

    params = functools.reduce(lambda x, y: getattr(x, f"__{operator}__")(y), query_spec)
    log.debug("Query parameters: %s", params)

    query = Project.objects.filter(params)
    return [
        dict(name=x.name, version=x.version, summary=x.summary) for x in query[:100]
    ]
