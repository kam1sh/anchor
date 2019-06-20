from __future__ import annotations

import enum
import functools
import logging
import typing as ty

from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.db.models import CharField, EmailField, Min, Model
from django.urls import reverse

log = logging.getLogger(__name__)


__all__ = ["User", "RoleType", "PermissionAware"]


class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField("Name of User", blank=True, max_length=255)
    # redefined field to make it unique and not blank
    email = EmailField("email address", blank=False, unique=True)

    # USERNAME_FIELD = "email"
    # # auth.E002
    # REQUIRED_FIELDS = []  # type: ignore

    def get_absolute_url(self):
        return reverse("users:details", kwargs={"username": self.username})

    def give_access(self, obj: PermissionAware, role: RoleLike):
        """ Gives user access to provided object. """
        roletype = to_roletype(role)
        role_obj = UserRole(user=self, level=roletype)
        role_obj.save()
        obj.user_roles.add(role_obj)

    def __str__(self):
        return self.email


class RoleType(enum.IntEnum):
    """ Enum with roles and their access levels """

    owner = 0
    maintainer = 10
    developer = 100
    guest = 200
    anonymous = 999


RoleLike = ty.Union[RoleType, str, int]


@functools.singledispatch
def to_roletype(value: RoleLike) -> RoleType:
    """ Converts value to RoleType. """
    raise ValueError(value)


@to_roletype.register
def _str(value: str):
    return getattr(RoleType, value.lower())


@to_roletype.register
def _rt(value: RoleType):
    return value


@to_roletype.register
def _int(value: int):
    return RoleType(value)


class Role(Model):
    level = models.PositiveIntegerField()

    def __str__(self):
        return self.name

    @property
    def name(self) -> str:
        try:
            return to_roletype(self.level).name
        except ValueError:
            return "<not set>"


class UserRole(Role):
    user = models.ForeignKey(User, on_delete=models.CASCADE)


class GroupRole(Role):
    group = models.ForeignKey(Group, on_delete=models.CASCADE)


class PermissionAware(models.Model):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    user_roles = models.ManyToManyField(UserRole)
    group_roles = models.ManyToManyField(GroupRole)

    _permissions: ty.Mapping[RoleLike, ty.Union[set, str]] = {}

    class Meta:
        abstract = True

    def has_role(self, user, role: RoleLike) -> bool:
        """ Checks if user has a role. """
        log.debug("owner: %r, user: %r", self.owner, user)
        return (
            self.owner == user
            or user.is_superuser
            or self.effective_level(user) <= to_roletype(role)
        )

    def effective_level(self, user) -> RoleType:
        """ Returns user role level, according to his groups. """
        if user == self.owner:
            return RoleType.owner
        try:
            user_level = self.user_roles.get(user=user).level
        except UserRole.DoesNotExist:
            user_level = RoleType.anonymous
        group_level = (
            self.group_roles.filter(group__in=user.groups.all()).aggregate(
                Min("level")
            )["level__min"]
            or 999
        )
        effective = min(user_level, group_level)
        return to_roletype(effective)

    def permissions_for(self, *, user: User = None, level: int = None) -> ty.Set[str]:
        """ Returns all permissions that user/role level has. """
        if not user and level is None:
            raise ValueError("Provide user or permissions level")
        user_level = level if level is not None else self.effective_level(user)
        result_perms = set()
        for perm, perms in self._permissions.items():
            if user_level <= to_roletype(perm):
                # perms may be one string insead of set
                if isinstance(perms, str):
                    result_perms.add(perms)
                else:
                    result_perms.update(perms)
        return result_perms

    def has_permission(self, user: User, permission: str) -> bool:
        """ Checks if user has required permission. """
        return (
            self.owner == user
            or user.is_superuser
            or permission in self.permissions_for(user=user)
        )
