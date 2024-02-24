import importlib.resources
import inspect
import logging
import os

from quart import Quart

logger = logging.getLogger(__name__)


def load_configuration(
    app: Quart,
    package: str = None,
    path: str = None,
    environment: str = None,
) -> str:
    if environment is None:
        environment = os.environ.get("ENVIRONMENT") or "development"

    if package is None:
        if path is None:
            path = os.environ.get("CONFIGURATIONS")

        if path is None:
            # load from a package called "{calling_package}.configurations"
            current_frame = inspect.currentframe()
            calling_package = current_frame.f_back.f_globals["__package__"]
            if calling_package:
                package = ".".join([calling_package, "configurations"])
            else:
                package = "configurations"

            with importlib.resources.as_file(importlib.resources.files(package) / f"{environment}.conf") as path:
                logger.info("loading configuration from '%s'", path)
                app.config.from_pyfile(path)
        else:
            path = os.path.join(path, "{}.conf".format(environment))
            logger.info("loading configuration from '%s'", path)
            app.config.from_pyfile(path)

    else:
        with importlib.resources.as_file(importlib.resources.files(package) / f"{environment}.conf") as path:
            logger.info("loading configuration from '%s'", path)
            app.config.from_pyfile(path)

    return environment
