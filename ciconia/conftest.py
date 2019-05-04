import logging

import pytest
from django.test import RequestFactory


def pytest_configure():
    # removes StreamHandler to avoid double logging (in stderr and pytest)
    logging.getLogger("ciconia").handlers = []


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()
