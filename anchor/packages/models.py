import dataclasses
import enum
import functools
import json
import logging
import typing as ty
from datetime import datetime, timedelta
from pathlib import Path

from django.core import files
from django.db import models
from django.utils import timezone
from guardian.models import UserObjectPermission

from ..exceptions import UserError
from ..users.models import User

log = logging.getLogger(__name__)


class PackageTypes(enum.Enum):
    Python = "python"
    RPM = "rpm"
    DEB = "deb"
    Docker = "docker"


@dataclasses.dataclass
class Metadata:
    """ Package file metadata. """

    name: str
    version: str
    summary: str
    description: str


class PermissionAware(models.Model):
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Meta:
        abstract = True

    def available_to(self, user, permission) -> bool:
        return (
            self.owner == user
            or user.is_superuser
            or user.has_perm(self._get_permission(permission), self)
        )

    def _get_permission(self, perm):
        return f"{perm}_{self._meta.model_name}"

    def give_access(self, user, permission):
        permission = self._get_permission(permission)
        log.debug("Assigning permission %s", permission)
        return UserObjectPermission.objects.assign_perm(permission, user, self)
        # return user.user_permissions.add(permission, self)


class Package(PermissionAware):
    """Base model that represents common package information."""

    pkg_type = models.CharField(
        max_length=16, db_index=True, choices=[(tag, tag.value) for tag in PackageTypes]
    )
    name = models.CharField(max_length=64, db_index=True)
    version = models.CharField("Latest version", max_length=64)
    summary = models.TextField(null=True)
    updated = models.DateTimeField("Last updated")
    # updated with the new package version
    description = models.TextField("Description", null=True)

    class Meta:
        unique_together = ["pkg_type", "name"]
        # index_together?

    def __init__(self, *args, metadata=None):
        super().__init__(*args)
        if metadata:
            self.from_metadata(metadata)

    def from_metadata(self, metadata):
        """Updates package info from pkg_file metadata."""
        self.name = metadata.name
        self.version = metadata.version
        self.summary = metadata.summary
        self.description = metadata.description
        self.update_time()

    def update_time(self):
        self.updated = timezone.now()

    def __str__(self):
        return self.name + " " + self.version


# TODO inherit django.core.files.File?
class ChunkedReader:
    """ File wrapper that supports chunk iterating. """

    def __init__(self, src: ty.BinaryIO, max_size_kb):
        self.name = src.name
        self.src = src
        self.size = -1
        self.max_size = max_size_kb * 1024

    def run(self):
        for _ in self:
            pass

    def __iter__(self):
        yield from self.chunks()

    def chunks(self, chunk_size=2 ** 20):
        size = 0
        while True:
            chunk = self.src.read(chunk_size)
            if not chunk:
                break
            size += len(chunk)
            if size > self.max_size:
                log.debug("Calculated size: %s", size)
                raise UserError(f"File size exceeds available ({self.max_size} bytes)")
            yield chunk
        if not size:
            raise UserError("Empty file")
        self.size = size

    @property
    def file(self):
        return files.File(self.src)


class PackageFile(PermissionAware):
    """Package file representation. Bounded to the package."""

    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    filename = models.CharField(max_length=64, unique=True)
    fileobj = models.FileField()
    size = models.IntegerField()
    version = models.CharField(max_length=64)
    uploaded = models.DateTimeField()

    def update(self, src: ChunkedReader, metadata):
        self.fileobj = src.file
        src.run()
        self.filename = Path(src.name).name
        self.size = src.size
        self.uploaded = timezone.now()
        self.version = metadata.version

    def __str__(self):
        return self.filename


class RetentionPolicy(models.Model):
    # right now anchor project is not so big to have reasons for many to many everywhere
    # applied_to = models.ManyToManyField(Package, null=True)
    applied_to = models.ForeignKey(Package, on_delete=models.CASCADE)
    _criteria = models.TextField("Retention settings (JSON)")
    schedule = None

    def __init__(self, *args):
        super().__init__(*args)
        self.criteria = json.loads(self._criteria or "{}")
        self.criteria.setdefault("keep", [])
        self.criteria.setdefault("drop", [])

    def for_pkg(self, pkg_type: PackageTypes, name: str):
        target = Package.objects.get(pkg_type=pkg_type, name=name)
        self.applied_to = target

    def keep(
        self, regexp: str = None, before_age: timedelta = None, size_less: int = None
    ):
        """
        Parameters that define conditions when files should be keep.
        This parameter has a higher priority over `drop`.
        """
        self.criteria["keep"].append(
            dict(regexp=regexp, before_age=before_age, size_less=size_less)
        )

    def drop(
        self, regexp: str = None, after_age: timedelta = None, size_exceeds: int = None
    ):
        self.criteria["drop"].append(
            dict(regexp=regexp, after_age=after_age, size_exceeds=size_exceeds)
        )

    def every(self, time: timedelta):
        self.schedule = time

    _pol_mapping = {
        "regexp": "version__iregex",
        "before_age": "uploaded__lt",
        "after_age": "uploaded__gt",
        "size_less": "size__lt",
        "size_exceeds": "size__gt",
    }

    def run(self, check=False):
        packages = PackageFile.objects.filter(package=self.applied_to)
        # this could be rewritten in sequence generator, but then it'll be hard to debug =/
        drop = self._reduce_policies(self.criteria["drop"])
        keep = self._reduce_policies(self.criteria["keep"])
        # TODO drop only if setting enabled and by soft/hard policy settings?
        log.debug("Queries:\n%s;\n%s", drop, keep)
        log.debug("Initial: %s", packages)
        packages = packages.filter(drop)
        log.debug("Filtered: %s", packages)
        packages = packages.exclude(keep)
        log.debug("Excluded: %s", packages)
        if check:
            return packages
        packages.delete()

    def _reduce_policies(self, policies: list) -> models.Q:
        out = []
        for policy in policies:
            param = {
                self._pol_mapping[key]: value
                for key, value in policy.items()
                if value is not None
            }
            out.append(models.Q(**param))
        return functools.reduce(lambda x, y: x | y, out, models.Q())

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        self._criteria = json.dumps(self._criteria)
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )
