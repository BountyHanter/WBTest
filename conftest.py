import pytest
from rest_framework.test import APIClient

pytest.DEBUG = False


@pytest.fixture
def client():
    return APIClient()


def pytest_addoption(parser):
    parser.addoption("--print", action="store_true", default=False)


def pytest_configure(config):
    pytest.DEBUG = config.getoption("--print")