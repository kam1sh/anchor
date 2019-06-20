from django.views.generic import View, DetailView as django_detail

from ..exceptions import LoginRedirect, Forbidden
from ..users.models import PermissionAware

__all__ = ["AccessMixin", "DetailView"]


class AccessMixin(View):
    def check_access(self, obj, permission: str):
        user = self.request.user
        if not obj.has_permission(user, permission):
            if not user.is_authenticated:
                raise LoginRedirect
            raise Forbidden


class DetailView(django_detail, AccessMixin):
    """ DetailView that supports access check """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset=queryset)
        self.check_access(obj, "read")
        return obj
