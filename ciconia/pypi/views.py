import logging

from django.db import transaction
from django.views import generic
from django.views.decorators import csrf
from django.utils.decorators import method_decorator
from django import http

from .models import PythonPackage, PackageVersion
from . import models

log = logging.getLogger(__name__)


@method_decorator(csrf.csrf_exempt, name="dispatch")
class PackageList(generic.ListView):
    model = PythonPackage
    context_object_name = "packages"
    template_name = "packages.html"

    def get_queryset(self):
        return self.model.objects.all()

    def post(self, request: http.HttpRequest):
        ra = request.META["REMOTE_ADDR"]
        # cl = request.META["CONTENT_LENGTH"] # could be useful in the future
        raw_file = request.FILES.get("content")
        if not raw_file:
            m = 'Provide package within "content" file.'
            return http.HttpResponseBadRequest(m)
        pkg_file = models.PackageFile(pkg=raw_file)
        log.debug("Got package %s from IP %s", pkg_file, ra)

        with transaction.atomic():
            try:
                pkg = PythonPackage.objects.get(name=pkg_file.name)
            except PythonPackage.DoesNotExist:
                pkg = PythonPackage(pkg_file=pkg_file)
            pkg.save()

            try:
                pkg_version = PackageVersion.objects.get(package=pkg)
            except PackageVersion.DoesNotExist:
                pkg_version = PackageVersion(pkg_file=pkg_file)

            pkg_version.package = pkg
            pkg_version.save()

            pkg_file.version = pkg_version
            pkg_file.save()

        return http.HttpResponse("OK!")


class PackageVersions(generic.ListView):
    template_name = "versions.html"
