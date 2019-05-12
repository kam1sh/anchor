import logging

import pytest

from anchor.users.models import User

from . import Client


def pytest_configure():
    # removes StreamHandler to avoid double logging (in stderr and pytest)
    logging.getLogger("anchor").handlers = []


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def client():
    return Client()


@pytest.yield_fixture(autouse=True)
def user(db):
    usr = User()
    usr.email = "test@localhost"
    usr.set_password("123")
    usr.save()
    try:
        yield
    finally:
        usr.delete()
