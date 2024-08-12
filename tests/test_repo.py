import importlib.metadata
from unittest.mock import patch

import enphase_proxy


def test_version_found():
    with patch.object(importlib.metadata, "version", return_value="1.2.3"):
        assert enphase_proxy.version("test_package") == "1.2.3"


def test_version_not_found():
    with patch.object(importlib.metadata, "version", side_effect=importlib.metadata.PackageNotFoundError):
        assert enphase_proxy.version("test_package") == "0.0.0"
