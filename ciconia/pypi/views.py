import logging

from django import http
from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators import csrf

from .models import PackageFile, PythonPackage

log = logging.getLogger(__name__)


@csrf.csrf_exempt
def upload_package(request):
    ra = request.META["REMOTE_ADDR"]
    # cl = request.META["CONTENT_LENGTH"] # could be useful in the future
    raw_file = request.FILES.get("content")
    if not raw_file:
        m = 'Provide package within "content" file.'
        return http.HttpResponseBadRequest(m)
    try:
        name = raw_file.name
        pkg_file = PackageFile.objects.get(filename=name)
        pkg_file.update(raw_file)
    except PackageFile.DoesNotExist:
        pkg_file = PackageFile(pkg=raw_file)
    log.debug("Got package %s from IP %s", pkg_file, ra)

    with transaction.atomic():
        try:
            pkg = PythonPackage.objects.get(name=pkg_file.name)
        except PythonPackage.DoesNotExist:
            pkg = PythonPackage(pkg_file=pkg_file)
        pkg.update_time()
        pkg.save()

        pkg_file.package = pkg
        pkg_file.save()

    return http.HttpResponse("OK!")


@method_decorator(csrf.csrf_exempt, name="dispatch")
class PackageList(generic.ListView):
    model = PythonPackage
    context_object_name = "packages"
    template_name = "packages.html"

    def get_queryset(self):
        return self.model.objects.all()


def files(request, name: str):
    """ Returns page with list of all existing files for the package. """
    result = PackageFile.objects.filter(package__name=name)
    return render(
        request,
        "versions.html",
        dict(title=f"{name.capitalize()} files", versions=result),
    )
