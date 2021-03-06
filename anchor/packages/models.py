import dataclasses
import enum
import functools
import json
import logging
import typing as ty
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from ..common.helpers import DataclassExtras
from ..exceptions import UserError
from ..users.models import PermissionAware

log = logging.getLogger(__name__)


class PackageTypes(enum.Enum):
    Python = "python"
    RPM = "rpm"
    DEB = "deb"
    Docker = "docker"


@dataclasses.dataclass
class Metadata(DataclassExtras):
    """ Package file metadata. """

    name: str
    version: str
    summary: str
    description: str


class Package(PermissionAware):
    """Base model that represents common package information."""

    pkg_type = models.CharField(
        max_length=16, db_index=True, choices=[(tag, tag.value) for tag in PackageTypes]
    )
    name = models.CharField(max_length=64, db_index=True)
    version = models.CharField("Latest version", max_length=64)
    summary = models.TextField(null=True)
    # various package attributes, set as JSON
    _attrs = models.TextField(default="{}")
    # updated with the new package version
    updated = models.DateTimeField("Last updated")
    downloads = models.IntegerField("Downloads count", default=0)
    public = models.BooleanField("Package visible to all", default=True)

    _permissions = {
        "maintainer": "remove_files",
        "developer": "upload",
        "guest": "read",
    }

    class Meta:
        unique_together = ["pkg_type", "name"]
        # index_together?

    def __init__(self, *args, metadata=None):
        super().__init__(*args)
        if metadata:
            self.from_metadata(metadata)

    def has_permission(self, user, permission):
        if permission == "read" and self.public:
            return True
        return super().has_permission(user, permission)

    def from_metadata(self, metadata):
        """Updates package info from pkg_file metadata."""
        self.name = metadata.name
        self.version = metadata.version
        self.summary = metadata.summary
        self.update_time()

    @property
    def files(self):
        return PackageFile.objects.filter(package=self)

    def stats(self):
        return self.files.aggregate(count=models.Count("*"), size=models.Sum("size"))

    def update_time(self):
        self.updated = timezone.now()

    def detail_url(self):
        return reverse("packages:details", kwargs={"id": self.id})

    def download_url(self) -> ty.Optional[str]:
        """
        Returns URL with latest available
        package file, if package has any.
        """
        return ""  # TODO

    def download_bundle(self):
        """
        Same as download_url, but instead of one file
        it returns archive with all dependencies.
        """
        return ""  # TODO

    def __str__(self):
        return self.name + " " + self.version


# TODO inherit django.core.files.File?
class ChunkedReader:
    """ File wrapper that supports chunk iterating. """

    def __init__(self, src: ty.BinaryIO, max_size_kb):
        self.name = src.name
        self.src = src
        self.size = 0
        self.max_size = max_size_kb * 1024

    def __iter__(self):
        yield from iter(lambda: self.read(2048), b"")

    def chunks(self):
        return iter(self)

    def read(self, size=None):
        chunk = self.src.read(size)
        self.size += len(chunk)
        if self.size > self.max_size:
            log.debug("Calculated size: %s", self.size)
            raise UserError(f"File size exceeds available ({self.max_size} bytes)")
        # end of file and size is still zero
        if not chunk:
            self.uploaded()
        return chunk

    def uploaded(self):
        """ Triggered when file has been uploaded. """
        if not self.size:
            raise UserError("Empty file")


class PackageFile(models.Model):
    """Package file representation. Bounded to the package."""

    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    filename = models.CharField(max_length=64, unique=True)
    fileobj = models.FileField()
    size = models.IntegerField()
    version = models.CharField(max_length=64)
    uploaded = models.DateTimeField("Uploaded")

    def update(self, src: ChunkedReader, metadata):
        self.fileobj.save(src.name, src, save=False)
        if src.size is 0:
            raise IOError("Storage didn't read the file (empty?)")
        log.debug("Saved file (%s bytes) to %s", src.size, self.path)
        self.filename = Path(src.name).name
        self.size = src.size
        self.uploaded = timezone.now()
        self.version = metadata.version

    @property
    def path(self) -> Path:
        if self.filename or self.fileobj.name:
            return Path(settings.MEDIA_ROOT, self.fileobj.name or self.filename)
        raise ValueError("There is no file")

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
