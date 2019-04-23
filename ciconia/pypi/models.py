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
    # one package version could contain multiple files (.tar.gz, .whl etc)
    version = models.ForeignKey(PackageVersion, on_delete=models.CASCADE)
    pkg_file = models.FileField(upload_to="pypi", name="File itself")


def new_package(pkg):
    PythonPackage()
