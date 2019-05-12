import base64
import random
import subprocess
import xmlrpc.client
from pathlib import Path

import pytest
from django.core.files.uploadedfile import File
from packaging.utils import canonicalize_version

import anchor
from anchor.pypi import models, service

PACKAGES = dict(
    sdist=next(Path("dist").glob("*.whl")),
    bdist_wheel=next(Path("dist").glob("*.tar.gz")),
)

FORM = {
    "name": "anchor",
    "version": "0.1.0",
    "filetype": "sdist",
    "pyversion": "",
    "metadata_version": "2.1",
    "summary": "Ciconia test package",
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


class PackageFactory:
    def __init__(self, tmpdir):
        self._tmpdir = tmpdir
        self._fds = []

    def new(self, **kwargs):
        form = FORM.copy()
        form.update(kwargs)
        filename = self._tmpdir / "{name}-{version}.tar.gz".format(**form)
        self._gen(filename)
        form["sha256_digest"] = sha256sum(filename)
        fd = filename.open("rb")
        self._fds.append(fd)
        form["file"] = open(filename, "rb")
        return form

    def _gen(self, path):
        with path.open("w") as fd:
            for _ in range(5):
                fd.write(str(random.randint(1, 9)) * 1024)

    def close_all(self):
        for fd in self._fds:
            fd.close()
        self._fds.clear()


@pytest.yield_fixture(scope="function")
def packages(tmp_path):
    factory = PackageFactory(tmp_path)
    try:
        yield factory
    finally:
        factory.close_all()


@pytest.fixture(scope="function")
def dist(packages):
    return packages.new()


@pytest.fixture
def package(dist, db):
    file_ = dist.pop("file")
    return service.new_package(dist, file_)


def sha256sum(pth: Path):
    return subprocess.check_output(
        ["sha256sum", pth.absolute()], encoding="utf-8"
    ).split()[0]


@pytest.mark.unit
def test_readers(dist):
    """Tests for package reading (wheel and tar.gz)"""
    file_ = dist.pop("file")
    pkg = models.PackageFile(pkg=file_, metadata=dist)
    origname = Path(file_.name).name
    assert pkg.filename == origname
    assert Path(pkg.fileobj.name).name == origname
    # metadata accessing
    assert pkg.name == "anchor"
    assert pkg.version == canonicalize_version(anchor.__version__)
    assert isinstance(pkg.metadata["requires_dist"], list)


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
