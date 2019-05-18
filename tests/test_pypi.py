import base64
import random
import subprocess
import xmlrpc.client
from pathlib import Path

import anchor
import pytest
from anchor.common.middleware import bind_form
from anchor.pypi import models, service
from anchor.pypi.models import Metadata
from django.core.files.uploadedfile import File
from packaging.utils import canonicalize_version

from . import PackageFactory

FORM = {
    "name": "anchor",
    "version": "0.1.0",
    "filetype": "sdist",
    "pyversion": "",
    "metadata_version": "2.1",
    "summary": "anchor test package",
    "home_page": "",
    "author": "Igor Ovsyannikov",
    "author_email": "kamish@outlook.com",
    "maintainer": "Igor Ovsyannikov",
    "maintainer_email": "kamish@outlook.com",
    "license": "MIT",
    "description": "",
    "keywords": "",
    "classifiers": [
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    "download_url": "",
    "comment": "",
    "sha256_digest": None,
    "requires_dist": ["flask (>=1.0,<2.0)", "docker (>=3.7,<4.0)"],
    "requires_python": ">=3.6,<4.0",
    ":action": "file_upload",
    "protocol_version": "1",
}


class PyPackageFactory(PackageFactory):
    def new_form(self, **kwargs):
        """ Creates new form with a file """
        form = FORM.copy()
        form.update(kwargs)
        filename = self._gen("{name}-{version}.tar.gz".format(**form))
        form["sha256_digest"] = sha256sum(filename)
        fd = filename.open("rb")
        self._fds.append(fd)
        form["file"] = fd
        return form

    def new(self, **kwargs):
        """ Create new package. """
        form = self.new_form(**kwargs)
        file_ = form.pop("file")
        return service.new_package(bind_form(form, Metadata), file_)


@pytest.yield_fixture(scope="function")
def pypackages(tmp_path):
    factory = PyPackageFactory(tmp_path)
    try:
        yield factory
    finally:
        factory.close_all()


@pytest.fixture(scope="function")
def dist(pypackages):
    return pypackages.new_form()


@pytest.fixture
def package(pypackages, db):
    return pypackages.new()


def sha256sum(pth: Path):
    return subprocess.check_output(
        ["sha256sum", pth.absolute()], encoding="utf-8"
    ).split()[0]


@pytest.mark.unit
def test_readers(dist):
    """Tests for package reading (wheel and tar.gz)"""
    file_ = dist.pop("file")
    form = bind_form(dist, Metadata)
    pkg = models.PackageFile(pkg=file_, metadata=form)
    origname = Path(file_.name).name
    assert pkg.filename == origname
    assert Path(pkg.fileobj.name).name == origname
    # metadata accessing
    assert pkg.name == "anchor"
    assert pkg.version == canonicalize_version(anchor.__version__)


def test_upload(dist, client, db):
    form = dist
    dist = dist.pop("file")
    form["content"] = File(dist)
    auth = "Basic: {}".format(base64.b64encode(b"test@localhost:123").decode())
    assert client.post("/py/upload/", form) == 401
    dist.seek(0)
    response = client.post("/py/upload/", form, HTTP_AUTHORIZATION=auth)
    print(response.content)
    assert response == 200


def test_download(package, client):
    assert client.get(f"/py/download/{package.filename}") == 200


def test_search(package, client):
    name = package.name
    data = xmlrpc.client.dumps((dict(name=[name]), "and"), "search")
    response = client.post("/py/", data=data, content_type="text/xml")
    assert response == 200
    assert name in response.content.decode()


def test_lists(package, client):
    name = package.name
    resp = client.get("/py/simple/")
    assert resp == 200
    assert name in resp.content.decode()
    resp = client.get(f"/py/simple/{name}/")
    assert resp == 200
    assert package.filename in resp.content.decode()
