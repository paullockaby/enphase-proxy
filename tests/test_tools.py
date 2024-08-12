import os

import pytest
from quart import Quart

from enphase_proxy.tools import load_configuration


@pytest.fixture
def mock_environment():
    os.environ["ENVIRONMENT"] = "foo"
    yield
    del os.environ["ENVIRONMENT"]


def test_load_configuration_no_environment():
    app = Quart(__name__)
    result = load_configuration(app)
    assert result == "development"


def test_load_configuration_with_environment():
    app = Quart(__name__)
    result = load_configuration(app, environment="asdf")
    assert result == "asdf"


def test_load_configuration_with_environment_in_environment(mock_environment):
    app = Quart(__name__)
    result = load_configuration(app)
    assert result == "foo"


def test_load_configuration_with_package():
    app = Quart(__name__)

    result = load_configuration(app, package="configurations", environment="development")
    assert result == "development"
    assert app.config["ENVIRONMENT"] == "development"

    result = load_configuration(app, package="configurations", environment="production")
    assert result == "production"
    assert app.config["ENVIRONMENT"] == "production"


def test_load_configuration_with_path():
    app = Quart(__name__)

    result = load_configuration(app, path="../src/configurations", environment="development")
    assert result == "development"
    assert app.config["ENVIRONMENT"] == "development"

    result = load_configuration(app, path="../src/configurations", environment="production")
    assert result == "production"
    assert app.config["ENVIRONMENT"] == "production"
