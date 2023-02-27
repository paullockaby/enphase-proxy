import logging

import aiohttp
from quart import Quart, Response, jsonify, make_response

from enphase import __version__

from .tools import load_configuration
from .updater import CredentialsUpdater


def load() -> Quart:
    app = Quart(__name__, static_folder=None)
    environment = load_configuration(app, package="configurations")
    app.config.from_prefixed_env("ENPHASE")
    app.logger.info(
        "starting web application in '{}' mode with version {}".format(
            environment,
            __version__,
        ),
    )

    # initialize the system that fetches the enphase jwt
    credentials_updater = CredentialsUpdater(app)

    # initialize a client connection pool for the local api
    @app.before_serving
    async def startup() -> None:
        app.config["LOCAL_API_SESSION"] = aiohttp.ClientSession(
            raise_for_status=True,
            base_url=app.config["LOCAL_API_URL"],
            skip_auto_headers={"User-Agent"},
        )

    @app.after_serving
    async def shutdown() -> None:
        if app.config["LOCAL_API_SESSION"]:
            await app.config["LOCAL_API_SESSION"].close()

    @app.route("/health")
    async def health() -> Response:
        return await make_response(
            jsonify(
                {
                    "status": "pass",
                    "message": "flux capacitor is fluxing",
                },
            ),
            200,
        )

    @app.route("/production")
    async def production() -> Response:
        api_key = credentials_updater.credentials
        async with app.config["LOCAL_API_SESSION"].get(
            "/production.json",
            ssl=False,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as r:
            data = await r.json()
            return await make_response(jsonify(data), 200)

    @app.route("/inverters")
    async def inverters() -> Response:
        api_key = credentials_updater.credentials
        async with app.config["LOCAL_API_SESSION"].get(
            "/api/v1/production/inverters",
            ssl=False,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as r:
            data = await r.json()
            return await make_response(jsonify(data), 200)

    # tell ourselves what we've mapped
    if app.logger.isEnabledFor(logging.DEBUG):
        for url in app.url_map.iter_rules():
            app.logger.debug(repr(url))

    return app
