from __future__ import annotations

import enum
import logging
import typing as ty

from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models import CharField, EmailField, Min, Model
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from guardian.models import UserObjectPermission

log = logging.getLogger(__name__)


__all__ = ["User", "RoleType", "PermissionAware"]


class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField(_("Name of User"), blank=True, max_length=255)
    # redefined field to make it unique and not blank
    email = EmailField("email address", blank=False, unique=True)

    # USERNAME_FIELD = "email"
    # # auth.E002
    # REQUIRED_FIELDS = []  # type: ignore

    def get_absolute_url(self):
        return reverse("users:details", kwargs={"username": self.username})

    def give_access(self, obj, role: RoleLike):
        roletype = to_roletype(role)
        role_obj = UserRole(user=self, level=roletype)
        role_obj.save()
        obj.user_roles.add(role_obj)

    def __str__(self):
        return self.email


def to_roletype(value: RoleLike) -> int:
    if isinstance(value, str):
        return getattr(RoleType, value.capitalize())
    elif isinstance(value, RoleType):
        return value
    elif isinstance(value, int):
        try:
            return RoleType(value)
        except ValueError:
            return value
    raise ValueError(value)


class RoleType(enum.IntEnum):
    Maintainer = 10
    Developer = 100
    Guest = 200


RoleLike = ty.Union[RoleType, str, int]


class Role(Model):
    level = models.PositiveIntegerField()

    def __str__(self):
        return str(self.value)

    @property
    def value(self) -> int:
        return to_roletype(self.level)


class UserRole(Role):
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class GroupRole(Role):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)


class PermissionAware(models.Model):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    user_roles = models.ManyToManyField(UserRole)
    group_roles = models.ManyToManyField(GroupRole)

    class Meta:
        abstract = True

    def available_to(self, user, role: RoleLike) -> bool:
        log.debug("owner: %r, user: %r", self.owner, user)
        return (
            self.owner == user
            or user.is_superuser
            or self._effective_user_role(user) <= to_roletype(role)
        )

    def _effective_user_role(self, user) -> int:
        user_level = self.user_roles.filter(user=user).aggregate(Min("level"))[
            "level__min"
        ]
        if user_level == 0:
            return RoleType.Maintainer
        group_level = self.group_roles.filter(group__in=user.groups.all()).aggregate(
            Min("level")
        )["level__min"]
        effective = min(user_level or 999, group_level or 999)
        return to_roletype(effective)

    def _get_permission(self, perm):
        return f"{perm}_{self._meta.model_name}"

    def give_access(self, user, permission):
        permission = self._get_permission(permission)
        log.debug("Assigning permission %s", permission)
        return UserObjectPermission.objects.assign_perm(permission, user, self)
        # return user.user_permissions.add(permission, self)
