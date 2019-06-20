from django.views.generic import ListView
from django.shortcuts import get_object_or_404

from .models import Package
from ..users.models import PermissionAware
from ..exceptions import LoginRedirect, Forbidden
from ..users.auth import DetailView, AccessMixin


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
        role = None
        if self.request.user and isinstance(self.object, PermissionAware):
            role = self.object.effective_level(self.request.user)
            context["role"] = getattr(role, "name", None)
            context["role_level"] = int(role)
            context["permissions"] = self.object.permissions_for(level=role)
            context["files"] = self.object.files[:10]

        return context


class FilesDetail(ListView, AccessMixin):
    def get_queryset(self):
        package = get_object_or_404(Package, id=self.kwargs["id"])
        self.check_access(package, "read")
        return package.files
