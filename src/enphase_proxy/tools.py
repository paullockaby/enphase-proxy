import importlib.resources
import logging
import os
from typing import Optional

from quart import Quart

logger = logging.getLogger(__name__)


def load_configuration(
    app: Quart,
    package: Optional[str] = None,
    path: Optional[str] = None,
    environment: Optional[str] = None,
) -> str:
    if environment is None:
        environment = os.environ.get("ENVIRONMENT") or "development"

    if package is None:
        if path is None:
            path = os.environ.get("CONFIGURATIONS")

        if path is not None:
            path = os.path.join(path, "{}.conf".format(environment))
            logger.info("loading configuration from '%s'", path)
            app.config.from_pyfile(path)

    else:
        configuration_path = importlib.resources.files(package) / f"{environment}.conf"
        with importlib.resources.as_file(configuration_path) as path:
            logger.info("loading configuration from '%s'", path)
            app.config.from_pyfile(path)

    return environment
