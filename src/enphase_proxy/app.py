import logging
from urllib.parse import urlencode

import httpx
from quart import Quart, jsonify, make_response, request
from quart.helpers import ResponseTypes

from enphase_proxy import __version__

from .tools import load_configuration
from .updater import CredentialsUpdater


def load() -> Quart:
    app = Quart(__name__, static_folder=None)
    environment = load_configuration(app, package="configurations")
    app.config.from_prefixed_env("ENPHASE")
    app.logger.info("starting web application in '%s' mode with version %s", environment, __version__)

    # initialize the system that fetches the enphase jwt
    credentials_updater = CredentialsUpdater(app)

    @app.route("/_/health")
    async def health() -> ResponseTypes:
        return await make_response(
            jsonify(
                {
                    "status": "pass",
                    "message": "flux capacitor is fluxing",
                    "version": __version__,
                }
            ),
            200,
        )

    @app.route("/", defaults={"path": ""}, methods=["HEAD", "GET", "POST"])
    @app.route("/<path:path>", methods=["HEAD", "GET", "POST"])
    async def proxy(path: str) -> ResponseTypes:
        destination = f"/{path}"
        args = dict(request.args.lists())
        if len(args):
            destination = f"{destination}?{urlencode(args, doseq=True)}"
        app.logger.debug("sending request for: %s", destination)

        async with httpx.AsyncClient(
            verify=False,  # noqa S501
            timeout=300,
            base_url=app.config["LOCAL_API_URL"],
        ) as client:
            result = await client.request(
                request.method,
                destination,
                headers={"Authorization": f"Bearer {credentials_updater.credentials}"},
            )
            content = result.text
            status_code = result.status_code

            response = await make_response(content, status_code)
            response.headers["Content-Type"] = result.headers.get("content-type")
            return response

    # tell ourselves what we've mapped
    if app.logger.isEnabledFor(logging.DEBUG):
        for url in app.url_map.iter_rules():
            app.logger.debug(repr(url))

    return app
