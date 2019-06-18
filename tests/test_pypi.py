import io
import subprocess
import xmlrpc.client
from pathlib import Path

import pytest
from packaging.utils import canonicalize_version

import anchor
from anchor.pypi import models, services
from anchor.pypi.models import Metadata, PackageFile, Project

from . import PackageFactory, TestCase, basic_auth
from .conftest import UserFactory

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
    ":action": "fileupload",
    "protocol_version": "1",
}


def sha256sum(pth: Path):
    return subprocess.check_output(
        ["sha256sum", pth.absolute()], encoding="utf-8"
    ).split()[0]


class PyPackageFactory(PackageFactory):
    def new_form(self, **kwargs) -> dict:
        """ Creates new form with a file """
        form = FORM.copy()
        form.update(kwargs)
        file = self.gen_file("{name}-{version}.tar.gz".format(**form))
        form["filename"] = file.name
        form["sha256_digest"] = sha256sum(file)
        fd = file.open("rb")
        form["content"] = fd
        return form

    def new(self, user=None, **kwargs):
        """ Create new package. """
        user = user or self.user
        form = self.new_form(**kwargs)
        file = form.pop("content")
        metadata = Metadata.from_dict(form)
        return services.upload_file(user, metadata, file)


############
# fixtures #
############


@pytest.yield_fixture
def pypackages(tmp_path):
    with PyPackageFactory(tmp_path) as factory:
        yield factory


@pytest.fixture
def form(pypackages):
    return pypackages.new_form()


@pytest.fixture
def file(pypackages, user):
    return pypackages.new(user=user)


@pytest.fixture
def upload(pypackages, client, db):
    def uploader(login=None, password=None, **kwargs):
        form = pypackages.new_form(**kwargs)
        kwargs = {}
        if login:
            basic_auth(login, password, request=kwargs)
        return client.post("/py/upload/", form, **kwargs)

    return uploader


#########
# tests #
#########


@pytest.mark.unit
def test_readers(form):
    """Tests for package reading (wheel and tar.gz)"""
    file = form.pop("content")
    file = models.ShaReader(file, 5120, assert_hash=form["sha256_digest"])
    metadata = Metadata.from_dict(form)
    pkg_file = PackageFile()
    pkg_file.update(src=file, metadata=metadata)
    origname = Path(file.name).name
    assert pkg_file.filename == origname
    assert Path(pkg_file.fileobj.name).name == origname
    # metadata accessing
    assert pkg_file.name == "anchor"
    assert pkg_file.version == canonicalize_version(anchor.__version__)


def test_anonymous_upload(upload):
    assert upload() == 401


def test_upload(upload, users):
    user = users.new(email="test2@localhost", login="test2")
    response = upload(login="test2@localhost", password="123")
    print(response.content)
    assert response == 200
    assert PackageFile.objects.all()
    assert PackageFile.objects.get().path.exists(), "File does not exists!"
    assert upload(login="test2@localhost", password="123") == 200
    assert upload(login="test2", password="123") == 200


def test_download(file, client):
    assert client.get(f"/py/download/{file.filename}") == 200
    file.package.refresh_from_db()
    assert file.package.downloads == 1


def test_search(file, client):
    name = file.name
    data = xmlrpc.client.dumps((dict(name=[name]), "and"), "search")
    response = client.post("/py/", data=data, content_type="text/xml")
    assert response == 200
    assert name in response


def test_lists(file, client):
    """ Lists of packages/files """
    name = file.name
    resp = client.get("/py/simple/")
    assert resp == 200
    assert name in resp
    resp = client.get(f"/py/simple/{name}/")
    assert resp == 200
    assert file.filename in resp
