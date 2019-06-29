from django.views.generic import ListView
from django.shortcuts import get_object_or_404, reverse

import humanize

from .models import Package
from ..users.models import PermissionAware
from ..exceptions import LoginRedirect, Forbidden
from ..users.auth import DetailView, AccessMixin
from ..common import html


class Index(ListView):
    model = Package
    template_name = "base.html"

    def get_queryset(self):
        """
        Returns list of packages that current user owns,
        otherwise list of public packages.
        """
        if self.request.user.is_authenticated:
            return self.model.objects.filter(owner=self.request.user)
        return self.model.objects.filter(public=True)


class PackageDetail(DetailView):
    model = Package
    template_name = "packages/detail.html"
    pk_url_kwarg = "id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user and isinstance(self.object, PermissionAware):
            # role = self.object.effective_level(self.request.user)
            # context["role"] = getattr(role, "name", None)
            # context["role_level"] = int(role)
            # context["permissions"] = self.object.permissions_for(level=role)
            files = self.object.files.order_by("uploaded")[:10]
            context["files"] = files
            context["files_table"] = FilesTable(files, paginate=False)
            context["stats"] = self.object.stats()
        return context


class FilesTable(html.Table):
    fields = ["filename", "version", "size", "uploaded"]

    def rows(self):
        for row in super().rows():
            link = '<a href="{}">{}</a>'.format(
                reverse("pypi.download", args=[row[0]]), row[0]
            )
            row[0] = link
            row[2] = humanize.naturalsize(row[2])
            row[3] = humanize.naturalday(row[3])
            yield row


class ListFiles(ListView, AccessMixin):
    package = None
    allow_empty = True

    def get_queryset(self):
        package = get_object_or_404(Package, id=self.kwargs["id"])
        self.package = package
        self.check_access(package, "read")
        return package.files

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context["package"] = self.package
        context["table"] = FilesTable(self.object_list, request=self.request)
        return context
