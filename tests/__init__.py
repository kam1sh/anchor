import random

import pytest
from anchor.packages.models import Package, PackageFile, PackageTypes
from anchor.pypi.models import Metadata
from django.test import Client as django_client

__all__ = ["Client"]


class Client(django_client):
    """
    Wrapper around django test client with a few extensions.
    """

    def request(self, **request):
        response = super().request(**request)
        return Response(response)


class Response:
    """
    Wrapper around HttpResponse with a few extra methods.
    """

    def __init__(self, response):
        self.orig = response

    def __getattr__(self, name):
        return getattr(self.orig, name)

    def __eq__(self, other):
        """
        Status code asserting:
        >>> assert resp == 200
        """
        if isinstance(other, int):
            return self.status_code == other
        return self.orig == other

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.status_code)

    def __str__(self):
        return str(self.orig)


def to_dataclass(data: dict, cls: type):
    """Converts dict to dataclass."""
    data = {k: v for k, v in data.items() if k in cls.__annotations__}
    return cls(**data)


class PackageFactory:
    """ Factory that creates abstract packages. """

    def __init__(self, tmp_path):
        self._tmppath = tmp_path
        self._fds = []
        self._last_pkg = None

    def new(self, name, version):
        """ Creates and saves new package object. """
        pkg = Package()
        pkg.name = name
        pkg.version = version
        pkg.pkg_type = "python"
        pkg.update_time()
        pkg.save()
        self._last_pkg = pkg
        return pkg

    def new_file(self, version, size=1, name=None):
        package = self._last_pkg if not name else Package.objects.get(name=name)
        pkg_file = PackageFile()
        pkg_file.version = version
        pkg_file.package = package
        fd = open(self._gen(f"{package.name}-{version}.tar.gz", size=size * 1024))
        self._fds.append(fd)
        pkg_file.update(fd)
        pkg_file.save()
        return pkg_file

    def _gen(self, name: str, size=5):
        """ Generates file. Size accepts kilobytes """
        filename = self._tmppath / name
        with filename.open("w") as fd:
            for _ in range(size):
                fd.write(str(random.randint(1, 9)) * 1024)
        return filename

    def close_all(self):
        for fd in self._fds:
            fd.close()
        self._fds.clear()
