import logging

from django.shortcuts import render
from django.views import generic, View
from django.views.decorators import csrf
from django.utils.decorators import method_decorator
from django import http

from .models import PythonPackage
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
        pkg = request.FILES.get("content")
        if not pkg:
            m = 'Provide package within "content" file.'
            return http.HttpResponseBadRequest(m)
        pf = models.PackageFile(pkg)
        log.debug("Got package %s from IP %s", pf, ra)

        return http.HttpResponse("OK!")


class PackageVersions(generic.ListView):
    template_name = "versions.html"
