import hashlib
import logging
import re
import tarfile
import typing as ty
import zipfile
from pathlib import Path

from django.conf import settings
from django.core import files
from django.db import models
from django.utils import timezone

log = logging.getLogger(__name__)

__all__ = ["PythonPackage", "PackageFile"]


class PythonPackage(models.Model):
    name = models.CharField(max_length=64, db_index=True)
    version = models.CharField("Latest version", max_length=16)
    summary = models.TextField(null=True)
    updated = models.DateTimeField("Last updated")
    # updated with the new package version
    info = models.TextField("Package information", null=True)

    def __init__(self, *args, pkg_file=None, pkg_ver=None):
        super().__init__(*args)
        if pkg_file:
            self.name = pkg_file.name
            self.version = pkg_file.version
        if pkg_ver:
            self.version = pkg_ver.tag
        self.updated = self.updated or timezone.now()

    def update_time(self):
        self.updated = timezone.now()

    def __str__(self):
        return self.name


class PackageFile(models.Model):
    # many to one, because one package version
    # could contain multiple files (.tar.gz, .whl etc)
    package = models.ForeignKey(PythonPackage, on_delete=models.CASCADE)
    filename = models.CharField(max_length=64)
    fileobj = models.FileField(upload_to="pypi")
    pkg_type = models.CharField(max_length=16)
    sha256 = models.CharField(max_length=64, unique=True)

    def __init__(self, *args, pkg=None, filename=None):
        super().__init__(*args)
        self._metadata = None
        if pkg:
            if not self._extract_name(pkg, filename):
                raise TypeError("Filename not provided")
            self.update(pkg)

    @property
    def metadata(self):
        if not self._metadata:
            with self.fileobj.open() as raw:
                self._metadata = self._extract_metadata(raw)
        return self._metadata

    @property
    def link(self):
        return str(Path(settings.MEDIA_URL, self.fileobj.name))

    @property
    def path(self):
        return Path(settings.MEDIA_ROOT, self.fileobj.name or self.filename)

    def update(self, src: ty.io.TextIO):
        if self.path.exists():
            self.path.unlink()
        self.fileobj = files.File(src, name=self.filename)
        src.seek(0)
        self._metadata = self._extract_metadata(src)
        src.seek(0)
        self._update_sha256(src)

    def _update_sha256(self, src) -> str:
        m = hashlib.sha256()
        for chunk in iter(lambda: src.read(2 ** 10), b""):
            m.update(chunk)
        self.sha256 = m.hexdigest()
        log.debug("%s sha256 sum: %s", self.filename, self.sha256)
        return self.sha256

    def _extract_name(self, pkg, filename):
        self.filename = Path(
            filename or getattr(pkg, "name", None) or getattr(pkg, "filename", None)
        ).name
        return self.filename

    def _extract_metadata(self, pkg) -> "WheelInfo":
        ext = self.filename.split(".")
        if ext[-1] == "whl":
            self.pkg_type = "wheel"
            return WheelInfo(pkg)
        if ext[-2:] == ["tar", "gz"]:
            self.pkg_type = "tar"
            return SdistInfo(pkg)
        raise ValueError("Could not recognize package format: %s" % ext)

    def __getattr__(self, key: str):
        """
        Simple way to access package info.
        >>> pkg.requires_python # -> ">=3.6,<4.0"
        """
        key = key.replace("_", "-")
        try:
            return self.metadata[key][0]
        except KeyError:
            raise AttributeError(key)

    def __str__(self):
        return self.filename


class WheelInfo(dict):
    """ Case-insensitive dictionary that stores wheel package metadata. """

    _pattern = re.compile(r"^([\w-]+): (.+)$")

    def __init__(self, fileobj):
        super().__init__()
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

    def __setitem__(self, key, value):
        return super().__setitem__(key.lower(), value)

    def __getitem__(self, key):
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
