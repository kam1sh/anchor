import zipfile
from pathlib import Path

from django.db import models


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

    def __init__(self, pkg, filename=None):
        super().__init__()
        if not self._extract_name(pkg, filename):
            raise TypeError("Filename not provided")
        if not hasattr(pkg, "read"):
            ext = str(pkg).split(".")[-1]

    def _extract_name(self, pkg, filename) -> str:
        self.filename = (
            Path(filename or "").name
            or getattr(pkg, "name", None)
            or getattr(pkg, "filename", None)
        )
        return self.filename

    def _unwrap_wheel(self, pkg):
        zf = zipfile.ZipFile
