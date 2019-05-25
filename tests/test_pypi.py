import base64
import random
import subprocess
import xmlrpc.client
from pathlib import Path

import anchor
import pytest
from anchor.common.middleware import bind_form
from anchor.pypi import services, models
from anchor.pypi.models import Metadata, PackageFile, Project
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
    ":action": "fileupload",
    "protocol_version": "1",
}


def sha256sum(pth: Path):
    return subprocess.check_output(
        ["sha256sum", pth.absolute()], encoding="utf-8"
    ).split()[0]


class PyPackageFactory(PackageFactory):
    def new_form(self, **kwargs):
        """ Creates new form with a file """
        form = FORM.copy()
        form.update(kwargs)
        filename = self.gen_file("{name}-{version}.tar.gz".format(**form))
        form["filename"] = filename.name
        form["sha256_digest"] = sha256sum(filename)
        fd = filename.open("rb")
        form["content"] = File(fd)
        return form

    def new(self, user=None, **kwargs):
        """ Create new package. """
        user = user or self.user
        form = self.new_form(**kwargs)
        file = form.pop("content")
        return services.upload_file(user, bind_form(form, Metadata), file)


############
# fixtures #
############


@pytest.yield_fixture
def pypackages(tmp_path, user):
    with PyPackageFactory(tmp_path, user) as factory:
        yield factory


@pytest.fixture
def form(pypackages):
    return pypackages.new_form()


@pytest.fixture
def package(pypackages):
    return pypackages.new()


@pytest.fixture
def upload(pypackages, client, db):
    def uploader(auth=None, **kwargs):
        form = pypackages.new_form(**kwargs)
        kwargs = {}
        if auth:
            kwargs["HTTP_AUTHORIZATION"] = "Basic: {}".format(
                base64.b64encode(auth.encode()).decode()
            )
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
    form = bind_form(form, Metadata)
    pkg_file = PackageFile()
    pkg_file.update(src=file, metadata=form)
    origname = Path(file.name).name
    assert pkg_file.filename == origname
    assert Path(pkg_file.fileobj.name).name == origname
    # metadata accessing
    assert pkg_file.name == "anchor"
    assert pkg_file.version == canonicalize_version(anchor.__version__)


def test_anonymous_upload(upload):
    assert upload() == 401


def test_upload(upload):
    response = upload(auth="test@localhost:123")
    print(response.content)
    assert response == 200
    assert PackageFile.objects.all()
    assert upload(auth="test@localhost:123") == 200


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
