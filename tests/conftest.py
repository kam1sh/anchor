import logging

import pytest
from anchor.users.models import User

from . import Client, PackageFactory


def pytest_configure():
    # removes StreamHandler to avoid double logging (in stderr and pytest)
    logging.getLogger("anchor").handlers = []


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def client():
    return Client()


class UserFactory:
    def new(self, email, password="123"):
        return User.objects.create_user(email, email=email, password=password)


@pytest.fixture
def users(db):
    return UserFactory()


@pytest.fixture(autouse=True)
def user(users):
    return users.new("test@localhost")


@pytest.yield_fixture(scope="function")
def packages(tmp_path, user):
    factory = PackageFactory(tmp_path, user)
    try:
        yield factory
    finally:
        factory.close_all()
