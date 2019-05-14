from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import re
import typing as ty
from pathlib import Path

import packaging.utils
import pkg_resources
import stdlib_list
from django.conf import settings
from django.core import files
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone

from ..packages.models import PackageTypes, Package
from ..common.exceptions import UserError

__all__ = ["Metadata", "Project", "PackageFile"]

log = logging.getLogger(__name__)
prohibited_packages = set(stdlib_list.stdlib_list("3.7"))
# TODO maybe also allow zip and egg?
allowed_files = re.compile(r".+\.(tar\.gz|whl)$", re.I)


EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


@dataclasses.dataclass
class Metadata:
    """ Dataclass with a few extra checks. """

    name: str
    version: str
    filetype: str
    metadata_version: str
    summary: str
    description: str
    sha256_digest: str

    def __post_init__(self):
        self.name = pkg_resources.safe_name(self.name)
        self.version = packaging.utils.canonicalize_version(self.version)
        if self.name in prohibited_packages:
            raise UserError(f"Name {self.name!r} conflicts with Python stdlib.")


class Project(Package):
    """Python project (set of packages)"""

    def __init__(self, *args):
        super().__init__(*args)
        pkg_type = PackageTypes.Python


class PackageFile(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    filename = models.CharField(max_length=64, unique=True)
    fileobj = models.FileField(upload_to="pypi")
    pkg_type = models.CharField(max_length=16)
    sha256 = models.CharField(max_length=64, unique=True)
    _metadata = models.TextField()

    def __init__(self, *args, pkg=None, metadata=None):
        super().__init__(*args)
        if metadata:
            self.metadata = metadata
        if pkg:
            if not self._extract_name(pkg):
                raise TypeError("Filename not provided")
            self.update(pkg)

    @property
    def metadata(self) -> Metadata:
        if not self._metadata:
            raise ValueError("No metadata available")
        return Metadata(**json.loads(self._metadata))

    @metadata.setter
    def metadata(self, val: Metadata):
        self.pkg_type = val.filetype
        self._metadata = json.dumps(val.__dict__)

    @property
    def link(self):
        return reverse("pypi.download", kwargs={"filename": self.name})

    @property
    def path(self) -> Path:
        if self.filename or self.fileobj.name:
            return Path(settings.MEDIA_ROOT, self.fileobj.name or self.filename)

    @property
    def size(self) -> int:
        return self.path.stat().st_size

    def update(self, src: ty.io.TextIO):
        if self.path and self.path.exists():
            self.path.unlink()
        self._extract_name(src)
        self.fileobj = files.File(src, name=self.filename)
        m = hashlib.sha256()
        for chunk in iter(lambda: src.read(2 ** 10), b""):
            m.update(chunk)
        self.sha256 = m.hexdigest()
        if self.sha256 == EMPTY_SHA256:
            raise UserError("Empty file")
        if self.sha256 != self.metadata.sha256_digest:
            raise UserError("Form digest does not match hashsum from the file")
        log.debug("%s sha256: %s", self.filename, self.sha256)

    def _extract_name(self, pkg, filename=None):
        filename = Path(
            filename or getattr(pkg, "name", None) or getattr(pkg, "filename", None)
        ).name
        if "/" in filename or "\\" in filename:
            raise UserError("Invalid file name")
        if not allowed_files.match(filename):
            raise UserError("Only wheel and tar.gz supported")
        self.filename = filename
        return filename

    def __str__(self):
        return self.filename

    def __getattr__(self, name):
        return getattr(self.metadata, name)
