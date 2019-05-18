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


@pytest.fixture(autouse=True)
def user(db):
    usr = User()
    usr.email = "test@localhost"
    usr.set_password("123")
    usr.save()
    return usr


@pytest.yield_fixture(scope="function")
def packages(tmp_path):
    factory = PackageFactory(tmp_path)
    try:
        yield factory
    finally:
        factory.close_all()
