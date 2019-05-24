import logging

from django.db import transaction

from ..exceptions import Forbidden
from .models import Package, PackageFile


class Uploader:
    """ Class that handles package file uploads """

    def __init__(self, pkg=Package, pkg_file=PackageFile, name=None):
        self.pkg = pkg
        self.pkg_file = pkg_file
        self.log = logging.getLogger(name or __name__)

    def __call__(self, user, metadata, fd):
        try:
            package = self.pkg.objects.get(name=metadata.name)
            if not package.available_to(user, "add"):
                raise Forbidden(f"You have no access to upload files in {package.name}")
        except self.pkg.DoesNotExist:
            package = self.pkg()
            package.owner = user
        package.from_metadata(metadata)

        try:
            pkg_file = self.pkg_file.objects.get(filename=fd.name)
            if not pkg_file.available_to(user, "change"):
                raise Forbidden("You have no access to rewrite this file")
        except self.pkg_file.DoesNotExist:
            pkg_file = self.pkg_file()
            pkg_file.owner = user
        pkg_file.update(fd, metadata)

        self.log.debug("Got package %s and package %s", pkg_file, package)
        with transaction.atomic():
            package.save()
            pkg_file.package = package
            pkg_file.save()
        return pkg_file


upload_file = Uploader()
