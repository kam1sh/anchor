from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import re
import typing as ty
from pathlib import Path

# https://github.com/pypa/packaging
import packaging.utils
import pkg_resources
import stdlib_list
from django.db import models
from django.urls import reverse

from ..exceptions import ServiceError, UserError
from ..packages import models as base_models

__all__ = ["Metadata", "Project", "PackageFile"]

log = logging.getLogger(__name__)
prohibited_packages = set(stdlib_list.stdlib_list("3.7"))
# TODO maybe also allow zip and egg?
allowed_files = re.compile(r".+\.(tar\.gz|whl)$", re.I)


@dataclasses.dataclass
class Metadata(base_models.Metadata):
    """
    Dataclass with a few extra checks.

    .. seealso:: https://packaging.python.org/specifications/core-metadata/
    """

    filetype: str
    metadata_version: str
    description: str
    sha256_digest: str

    def __post_init__(self):
        self.name = pkg_resources.safe_name(self.name)
        self.version = packaging.utils.canonicalize_version(self.version)
        if self.name in prohibited_packages:
            raise UserError(f"Name {self.name!r} conflicts with Python stdlib.")


class Project(base_models.Package):
    """Python project (set of packages)"""

    def __init__(self, *args):
        super().__init__(*args)
        self.pkg_type = base_models.PackageTypes.Python.value


class ShaReader(base_models.ChunkedReader):
    """ Wrapper around binary reader with sha256 computing. """

    def __init__(self, src, max_size_kb, assert_hash=None):
        super().__init__(src, max_size_kb)
        self.hash = assert_hash
        self.sha256 = None
        self._sha256 = hashlib.sha256()

    def read(self, size=None):
        chunk = super().read(size)
        self._sha256.update(chunk)
        return chunk

    def uploaded(self):
        super().uploaded()
        self.sha256 = self._sha256.hexdigest()
        if self.sha256 != self.hash:
            raise UserError(
                f"Form checksum does not match checksum from the file {self.sha256}"
            )


class PackageFile(base_models.PackageFile):
    dist_type = models.CharField(max_length=16)
    sha256 = models.CharField(max_length=64, unique=True)
    _metadata = models.TextField()

    @property
    def metadata(self) -> Metadata:
        if not self._metadata:
            raise ValueError("No metadata available")
        return Metadata(**json.loads(self._metadata))

    @metadata.setter
    def metadata(self, val: Metadata):
        self.dist_type = val.filetype
        self._metadata = json.dumps(val.__dict__)

    @property
    def link(self):
        return reverse("pypi.download", kwargs={"filename": self.name})

    def update(self, src, metadata):
        super().update(src, metadata)
        self.metadata = metadata
        self._extract_name(src)
        self.sha256 = src.sha256
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
        try:
            return getattr(self.metadata, name)
        except AttributeError:
            raise AttributeError(name) from None
