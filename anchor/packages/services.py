import logging
import typing as ty

from django.db import transaction

from ..exceptions import Forbidden
from .models import ChunkedReader, Package, PackageFile


class Uploader:
    """ Class that handles package file uploads """

    pkg = Package
    pkg_file = PackageFile
    reader = ChunkedReader

    def __init__(self, name: str = None):
        self.log = logging.getLogger(name or __name__)
        self.user = None
        self.metadata = None
        self.fd: ty.BinaryIO

    def get_reader(self):
        return self.reader(self.fd, max_size_kb=2 ** 20)  # 1GB hard limit TODO

    def __call__(self, user, metadata, fd):
        self.user = user
        self.metadata = metadata
        self.fd = fd
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
        reader = self.get_reader()
        pkg_file.update(reader, metadata)

        self.log.debug("Got package %s and package %s", pkg_file, package)
        with transaction.atomic():
            package.save()
            pkg_file.package = package
            pkg_file.save()
        return pkg_file


upload_file = Uploader()
