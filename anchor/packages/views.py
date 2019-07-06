from django.views.generic import View, ListView
from django.shortcuts import get_object_or_404, reverse

import humanize

from .models import Package
from ..users.auth import DetailView, AccessMixin
from ..common import html


class PackageSidebar(html.Sidebar):
    def __init__(self, active_num, pkg):
        super().__init__(active_num, pkg)
        self.pkg = pkg

    def items(self):
        return [
            (self.pkg.detail_url(), "Overview"),
            (reverse("packages:files", args=[self.pkg.id]), "Files"),
            ("#", "Settings"),
            ("#", "Permissions"),
        ]


class SidebarSupport(html.SidebarMixin):
    sidebar = PackageSidebar


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


class PackageDetail(DetailView, SidebarSupport):
    model = Package
    template_name = "packages/detail.html"
    pk_url_kwarg = "id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # if self.request.user and isinstance(self.object, PermissionAware):
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


class FilesActionsTable(FilesTable):
    fields = FilesTable.fields + [""]

    def rows(self):
        for row in super().rows():
            row.append(
                html.DropdownButtons(
                    parent=row,
                    button="Actions",
                    contents={"delete": "#", "rename": "#"},
                )
            )
            yield row


class ListFiles(ListView, AccessMixin, SidebarSupport):
    package = None
    object = None
    allow_empty = True
    sidebar_active = 1

    def get_queryset(self):
        package = get_object_or_404(Package, id=self.kwargs["id"])
        self.package = package
        self.object = package
        self.check_access(package, "read")
        return package.files

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(object_list=object_list, **kwargs)
        context["object"] = self.package
        context["table"] = FilesActionsTable(self.object_list, request=self.request)
        return context
