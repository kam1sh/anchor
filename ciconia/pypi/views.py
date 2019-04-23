import logging

from django.shortcuts import render
from django.views import generic, View
from django.views.decorators import csrf
from django.utils.decorators import method_decorator
from django import http

from .models import PythonPackage

log = logging.getLogger(__file__)

@method_decorator(csrf.csrf_exempt, name="dispatch")
class PackageList(generic.ListView):
    model = PythonPackage
    context_object_name = "packages"
    template_name = "packages.html"

    def get_queryset(self):
        return self.model.objects.all()
    
    def post(self, request: http.HttpRequest):
        ra = request.META["REMOTE_ADDR"]
        cl = request.META["CONTENT_LENGTH"]
        pkg = request.FILES.get("content")
        if not pkg:
            m = 'Provide package within "content" file.'
            return http.HttpResponseBadRequest(m)
        log.debug("Got package: %s", pkg)
        return http.HttpResponse("OK!")

class PackageVersions(generic.ListView):
    template_name = "versions.html"



