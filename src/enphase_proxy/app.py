import logging
from urllib.parse import urlencode

import aiohttp
from quart import Quart, Response, jsonify, make_response, request

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

    # initialize a client connection pool for the local api
    @app.before_serving
    async def startup() -> None:
        app.config["LOCAL_API_SESSION"]: aiohttp.ClientSession = aiohttp.ClientSession(
            base_url=app.config["LOCAL_API_URL"],
            skip_auto_headers={"User-Agent"},
        )

    @app.after_serving
    async def shutdown() -> None:
        if app.config["LOCAL_API_SESSION"]:
            await app.config["LOCAL_API_SESSION"].close()

    @app.route("/_/health")
    async def health() -> Response:
        return await make_response(
            jsonify({
                "status": "pass",
                "message": "flux capacitor is fluxing",
                "version": __version__,
            }), 200)

    @app.route("/", defaults={"path": ""}, methods=["HEAD", "GET", "POST"])
    @app.route("/<path:path>", methods=["HEAD", "GET", "POST"])
    async def proxy(path: str) -> Response:
        destination = f"/{path}"
        args = dict(request.args.lists())
        if len(args):
            destination = f"{destination}?{urlencode(args, doseq=True)}"
        app.logger.debug("sending request for: %s", destination)

        async with app.config["LOCAL_API_SESSION"].request(
                request.method,
                destination,
                ssl=False,
                headers={"Authorization": f"Bearer {credentials_updater.credentials}"},
        ) as result:
            content = await result.text()
            status_code = result.status
            content_type = result.headers.get("content-type")

            response = await make_response(content, status_code)
            response.headers["Content-Type"] = content_type
            return response

    # tell ourselves what we've mapped
    if app.logger.isEnabledFor(logging.DEBUG):
        for url in app.url_map.iter_rules():
            app.logger.debug(repr(url))

    return app
