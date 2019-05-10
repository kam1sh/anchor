from __future__ import annotations

import hashlib
import json
import logging
import re
import tarfile
import typing as ty
import zipfile
from pathlib import Path

import packaging.utils
import pkg_resources
import stdlib_list
from django.http import QueryDict
from django.conf import settings
from django.core import files
from django.db import models
from django.shortcuts import reverse
from django.utils import timezone

__all__ = ["Metadata", "Project", "PackageFile"]

log = logging.getLogger(__name__)
prohibited_packages = set(stdlib_list.stdlib_list("3.7"))
# TODO maybe also allow zip and egg?
allowed_files = re.compile(r".+\.(tar\.gz|whl)$", re.I)


EMPTY_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class Metadata(dict):
    """ Dict with a few checks for django QueryDict and version formatting. """

    def __init__(self, form: dict = None):
        if isinstance(form, QueryDict):
            super().__init__()
            for key in form:
                if key in {"classifiers", "requires_dist"}:
                    self[key] = form.getlist(key)
                else:
                    self[key] = form[key]
        else:
            super().__init__(**form)
        self["name"] = pkg_resources.safe_name(self["name"])
        self["version"] = packaging.utils.canonicalize_version(self["version"])
        if self["name"] in prohibited_packages:
            raise ValueError(f"Name {self.name!r} conflicts with Python stdlib.")

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as e:
            raise AttributeError(name) from e


class Project(models.Model):
    name = models.CharField(max_length=64, db_index=True)
    version = models.CharField("Latest version", max_length=16)
    summary = models.TextField(null=True)
    updated = models.DateTimeField("Last updated")
    # updated with the new package version
    info = models.TextField("Package information", null=True)

    def from_metadata(self, metadata: Metadata):
        """ Updates package info from pkg_file metadata. """
        self.name = metadata.name
        self.version = metadata.version
        self.summary = metadata.summary
        self.info = metadata.description

    def update_time(self):
        self.updated = timezone.now()

    def __str__(self):
        return self.name + " " + self.version


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
            self.metadata = self._extract_metadata(self.fileobj)
        return Metadata(json.loads(self._metadata))

    @metadata.setter
    def metadata(self, raw: dict):
        val = Metadata(raw)
        self._metadata = json.dumps(val)

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
            raise ValueError("Empty file")
        if self.sha256 != self.metadata["sha256_digest"]:
            raise ValueError("Form digest does not match hashsum from the file")
        log.debug("%s sha256: %s", self.filename, self.sha256)

    def _extract_name(self, pkg, filename=None):
        filename = Path(
            filename or getattr(pkg, "name", None) or getattr(pkg, "filename", None)
        ).name
        if "/" in filename or "\\" in filename:
            raise ValueError("Invalid file name")
        if not allowed_files.match(filename):
            raise ValueError("Only wheel and tar.gz supported")
        self.filename = filename
        return filename

    def _extract_metadata(self, pkg) -> "WheelInfo":
        ext = self.filename.split(".")
        if ext[-1] == "whl":
            self.pkg_type = "wheel"
            return WheelInfo(pkg)
        if ext[-2:] == ["tar", "gz"]:
            self.pkg_type = "tar"
            return SdistInfo(pkg)
        raise ValueError(f"Could not recognize package format: {ext!r}")

    def __str__(self):
        return self.filename

    def __getattr__(self, name):
        try:
            return self.metadata[name]
        except KeyError as e:
            raise AttributeError(name) from e


class WheelInfo(dict):
    """Case-insensitive dictionary that stores wheel package metadata."""

    _pattern = re.compile(r"^([\w-]+): (.+)$")

    def __init__(self, fileobj=None, **kwargs):
        super().__init__(**kwargs)
        if not fileobj:
            return
        self._reader = (x.decode().rstrip() for x in self._prepare_file(fileobj))

        for i, line in enumerate(self._check_description()):
            match = self._pattern.match(line)
            if not match:
                log.warning("could not read metadata at line %s", i + 1)
                continue
            key, val = match.groups()
            log.debug("%s=%s", key, val)
            self.setdefault(key.lower(), []).append(val)

    def _prepare_file(self, pkg):
        zf = zipfile.ZipFile(pkg)
        # all files from .dist-info in root folder
        dist_info = {
            x.name: str(x)
            for x in map(Path, zf.namelist())
            if not x.parent.parent.name and x.parent.name.endswith(".dist-info")
        }
        with zf.open(dist_info["METADATA"]) as raw:
            yield from raw

    def _check_description(self):
        for line in self._reader:
            if not line:
                # use the same iterator to skip those lines in the next iteration
                self["description"] = "\n".join(self._reader)
                break
            yield line

    def __getattr__(self, key: str):
        """
        Simple way to access package info.
        >>> pkg.requires_python # -> ">=3.6,<4.0"
        """
        key = key.replace("_", "-")
        try:
            return self[key][0]
        except KeyError:
            raise AttributeError(key)

    def __setitem__(self, key, value):
        value = value if isinstance(value, list) else [value]
        return super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
        """ Low-level access  """
        return super().__getitem__(key.lower())


class SdistInfo(WheelInfo):
    _continue = re.compile(r"^        (.+)$")

    def _prepare_file(self, pkg):
        tf = tarfile.open(fileobj=pkg, mode="r:gz")
        pkg_dir = {
            x.name: str(x)
            for x in map(Path, tf.getnames())
            if not x.parent.parent.parent.name
        }
        with tf.extractfile(pkg_dir["PKG-INFO"]) as raw:
            yield from raw

    def _check_description(self):
        desc = []
        for line in self._reader:
            match = self._continue.match(line)
            if match:
                desc.append(match.group(1))
            else:
                yield line
        self["description"] = "\n".join(desc)
