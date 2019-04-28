import gzip
import logging
import re
import tarfile
import typing as ty
import zipfile
from pathlib import Path

from django.core.files import File
from django.db import models

log = logging.getLogger(__name__)


class PythonPackage(models.Model):
    name = models.CharField(max_length=64, db_index=True)
    version = models.CharField("Latest version", max_length=16)
    updated = models.DateTimeField("Last updated")
    # updated with the new package version
    info = models.TextField("Package information")


class PackageVersion(models.Model):
    package = models.ForeignKey(PythonPackage, on_delete=models.CASCADE)
    tag = models.CharField(max_length=32)
    info = models.TextField("Package information")


class PackageFile(models.Model):
    # many to one, because one package version
    # could contain multiple files (.tar.gz, .whl etc)
    version = models.ForeignKey(PackageVersion, on_delete=models.CASCADE)
    filename = models.CharField(max_length=64)
    pkg_file = models.FileField(upload_to="pypi", name="File itself")
    pkg_type = models.CharField(max_length=16)

    def __init__(self, pkg, filename=None):
        super().__init__()
        if not self._extract_name(pkg, filename or ""):
            raise TypeError("Filename not provided")
        self.pkg_file = File(pkg, name=self.filename)
        pkg.seek(0)
        self.metadata = self._extract_metadata(pkg)

    def _extract_name(self, pkg, filename: str) -> str:
        self.filename = Path(
            filename or getattr(pkg, "name", None) or getattr(pkg, "filename", None)
        ).name
        return self.filename

    def _extract_metadata(self, pkg) -> "WheelMetadata":
        ext = self.filename.split(".")
        if ext[-1] == "whl":
            self.pkg_type = "wheel"
            return WheelInfo(pkg)
        if ext[-2:] == ["tar", "gz"]:
            self.pkg_type = "tar"
            return SdistInfo(pkg)
        raise ValueError("Could not recognize package format: %s" % ext)


class WheelInfo(dict):
    """ Case-insensitive dictionary that stores wheel package metadata. """

    _pattern = re.compile(r"^([\w-]+): (.+)$")

    def __init__(self, lines: ty.Iterable[bytes] = None):
        super().__init__()
        if lines:
            lines = self._prepare_file(lines)

        for i, line in enumerate(self._check_description(lines or [])):
            match = self._pattern.match(line)
            if not match:
                log.warning("could not read metadata at line %s", i + 1)
                continue
            key, val = match.groups()
            log.debug("%s=%s", key, val)
            self[key] = val

    def _prepare_file(self, pkg):
        zf = zipfile.ZipFile(pkg)
        # all files from .dist-info folder
        dist_info = {
            x.name: str(x)
            for x in map(Path, zf.namelist())
            if not x.parent.parent.name and x.parent.name.endswith(".dist-info")
        }
        with zf.open(dist_info["METADATA"]) as raw:
            yield from raw

    def _check_description(self, lines):
        lines_iter = iter(x.decode().rstrip() for x in lines)
        for line in lines_iter:
            if not line:
                # use the same iterator to skip those lines in the next iteration
                self["description"] = "\n".join(lines_iter)
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

    def _check_description(self, lines):
        lines_iter = iter(x.decode().rstrip() for x in lines)
        desc = []
        for line in lines_iter:
            match = self._continue.match(line)
            if match:
                desc.append(match.group(1))
            else:
                yield line
        self["description"] = "\n".join(desc)
