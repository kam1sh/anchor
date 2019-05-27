import random
import typing as ty
import unittest
from pathlib import Path

import pytest
from anchor.common.middleware import bind_form
from anchor.packages import services
from anchor.packages.models import Metadata, Package, PackageFile, PackageTypes
from django.test import Client as django_client
from django.test import TestCase as django_testcase

__all__ = ["Client"]


class Client(django_client):
    """
    Wrapper around django test client with a few extensions.
    """

    def request(self, **request):
        response = super().request(**request)
        return Response(response)


class Response:
    """ Wrapper around HttpResponse with a few extra methods. """

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

    def __contains__(self, value):
        """
        Response body checking:
        >>> assert "<HTML>" in resp
        """
        return value in self.orig.content.decode()

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.status_code)

    def __str__(self):
        return str(self.orig)


def to_dataclass(data: dict, cls: type):
    """Converts dict to dataclass."""
    data = {k: v for k, v in data.items() if k in cls.__annotations__}
    return cls(**data)


class _HookedPath:
    def __init__(self, *args, fd_list):
        self.path = Path(*args)
        self._fds = fd_list

    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        fd = self.path.open(mode, buffering, encoding, errors, newline)
        self._fds.append(fd)
        return fd

    def __getattr__(self, name):
        return getattr(self.path, name)


class PackageFactory:
    """ Factory that creates abstract packages. """

    def __init__(self, tmp_path, user=None):
        self._tmppath = tmp_path
        self._fds: ty.List[ty.BinaryIO] = []
        self._last_pkg = None
        self.user = user

    def new_metadata(self, **kwargs):
        form = dict(name="anchor", version="0.1.0", summary="", description="")
        form.update(kwargs)
        return bind_form(form, Metadata)

    def new_package(self, name="anchor"):
        """ Creates and saves new package object. """
        pkg = Package()
        pkg.name = name
        # pkg.version = version
        pkg.pkg_type = "python"
        pkg.owner = self.user
        pkg.update_time()
        pkg.save()
        self._last_pkg = pkg
        return pkg

    def new_file(self, user=None, size_kb=1, **kwargs):
        user = user or self.user
        metadata = self.new_metadata(**kwargs)
        filename = self.gen_file(
            f"{metadata.name}-{metadata.version}.tar.gz", size_kb=size_kb
        )
        file = filename.open("rb")
        self._fds.append(file)
        pkg_file = services.upload_file(user, metadata, file)
        return pkg_file

    def gen_file(self, name: str, size_kb=5) -> _HookedPath:
        """ Generates file. Size accepts kilobytes """
        filename = _HookedPath(self._tmppath, name, fd_list=self._fds)
        with filename.open("w") as fd:
            for _ in range(size_kb):
                fd.write(str(random.randint(1, 9)) * 1024)
        return filename

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, tb):
        for fd in self._fds:
            fd.close()
        self._fds.clear()
