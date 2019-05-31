import logging

import pytest
from anchor.users.models import User

from . import Client, PackageFactory, RequestFactory


def pytest_configure():
    # removes StreamHandler to avoid double logging (in stderr and pytest)
    logging.getLogger("anchor").handlers = []


@pytest.fixture(autouse=True)
def media_storage(settings, tmp_path):
    media = tmp_path / "media"
    media.mkdir()
    settings.MEDIA_ROOT = media.absolute()


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def requests():
    return RequestFactory()


class UserFactory:
    def new(self, email, password="123"):
        return User.objects.create_user(email, email=email, password=password)


@pytest.fixture
def users(db):
    return UserFactory()


@pytest.fixture
def user(users):
    usr = users.new("test@localhost")
    try:
        yield usr
    finally:
        usr.delete()


@pytest.yield_fixture
def tempfile(tmp_path):
    with PackageFactory(tmp_path) as factory:
        yield factory.gen_file


@pytest.yield_fixture
def packages(tmp_path, user):
    with PackageFactory(tmp_path, user) as factory:
        yield factory
