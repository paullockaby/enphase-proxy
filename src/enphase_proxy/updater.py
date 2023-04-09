import asyncio
import contextlib
import logging
from datetime import datetime
from time import perf_counter as time_now
from typing import Optional

import aiohttp
import tenacity
from quart import Quart

logger = logging.getLogger(__name__)


class CredentialsUpdater:
    def __init__(self: "CredentialsUpdater", app: Quart = None) -> None:
        # this is how often we will refresh our credentials. we are not
        # actually fetching credentials this often. this is just how often we
        # will check to see if we do need to fetch credentials. credentials
        # are only fetched when they're about to expire.
        self.updater_refresh = 300

        # if this is set to true then we are trying to exit. use an Event
        # instead of a flag so that we can wait on it and exit more quickly.
        self.updater_canceled = asyncio.Event()

        # this is the data that we're going to store/cache and the system for
        # fetching that data.
        self.data_cache: Optional[str] = None
        self.data_manager: Optional[CredentialsManager] = None

        if app is not None:
            self.init_app(app)
        else:
            self.app = None

    def init_app(self: "CredentialsUpdater", app: Quart = None) -> None:
        self.app = app
        self.data_manager = CredentialsManager(
            url=app.config.get("REMOTE_API_URL"),
            username=app.config.get("REMOTE_API_USERNAME"),
            password=app.config.get("REMOTE_API_PASSWORD"),
            serialno=app.config.get("REMOTE_API_SERIALNO"),
            # if this is present then we will not fetch anything
            jwt=app.config.get("LOCAL_API_JWT"),
        )

        @app.before_serving
        async def startup() -> None:
            # first fetch our credentials before the application starts. then
            # we are going to start a background task that will continue to
            # fetch the credentials on a regular basis. we can't start until
            # we have credentials so just crash if we can't fetch them.
            self.app.logger.info("fetching initial credentials")
            self.data_cache = await self.data_manager.credentials

            self.app.logger.info("registering credentials updater background task")
            app.add_background_task(self._background_looper)

        @app.after_serving
        async def shutdown() -> None:
            # just set the Event flag and the background task will exit. if the
            # background task does not exit within 60 seconds then Quart will
            # send an async cancel event to the task.
            self.app.logger.info(
                "signaling credentials updater background task to stop",
            )
            self.updater_canceled.set()

    async def _background_waiter(
        self: "CredentialsUpdater",
        event: asyncio.Event,
        timeout: int = 0,
    ) -> bool:
        # suppress TimeoutError because we'll return False in case of timeout
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(event.wait(), timeout)
        return event.is_set()

    async def _background_looper(self: "CredentialsUpdater") -> None:
        with contextlib.suppress(asyncio.CancelledError):
            while not await self._background_waiter(
                self.updater_canceled,
                self.updater_refresh,
            ):
                # we need the background task to keep looping and try again
                # so ignore any error that comes out of it and start again
                with contextlib.suppress(Exception):
                    await self._background_task()

        self.app.logger.info("credentials updater background task shutting down")

    async def _background_task(self: "CredentialsUpdater") -> None:
        # Randomly wait up to 2^x * 10 seconds between each retry, at least 60
        # seconds until the range reaches 600 seconds, then randomly up to 600
        # seconds afterward. If we were told to cancel then stop retrying.
        @tenacity.retry(
            wait=tenacity.wait_random_exponential(multiplier=10, min=60, max=600),
            stop=tenacity.stop_when_event_set(self.updater_canceled),
            before_sleep=tenacity.before_sleep_log(self.app.logger, logging.ERROR),
            reraise=True,
        )
        async def task() -> None:
            try:
                self.data_cache = await self.data_manager.credentials
            except Exception as e:
                self.app.logger.exception(f"unable to fetch credentials: {e}")
                raise

        timer = time_now()
        await task()
        self.app.logger.info(
            "finished refreshing credentials in {:.4f} seconds".format(
                time_now() - timer,
            ),
        )

    @property
    def credentials(self: "CredentialsUpdater") -> str:
        return self.data_cache


class CredentialsManager:
    def __init__(
        self: "CredentialsManager",
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        serialno: Optional[str] = None,
        jwt: Optional[str] = None,
    ) -> None:
        self.enphase_url = url
        self.enphase_username = username
        self.enphase_password = password
        self.enphase_serialno = serialno
        self.enphase_jwt = jwt

        self.data: Optional[dict] = None
        # {
        #     "fetched": None, # this is when we last fetched the jwt
        #     "expiry": None,  # this is when the jwt alleges to expire
        #     "token": None,   # this is the jwt that can be used for the api
        # }

    @property
    async def credentials(self: "CredentialsManager") -> str:
        if self.enphase_jwt:
            logger.debug("using a locally provided token")
            return self.enphase_jwt

        # we haven't fetched any credentials yet
        if self.data is None:
            logger.info("no credentials known -- fetching new credentials")
            self.data = await self._fetch_credentials()

        # if the credentials are closer to their expiration than to their
        # creation then fetch new ones
        now = datetime.now()
        if (now - self.data["fetched"]) > (self.data["expiry"] - now):
            logger.info(
                f"credentials will expire at {self.data['expiry']} -- fetching new credentials",
            )
            self.data = await self._fetch_credentials()

        return self.data["token"]

    async def _fetch_credentials(self: "CredentialsManager") -> dict:
        async with aiohttp.ClientSession(
            raise_for_status=True,
            base_url=self.enphase_url,
            skip_auto_headers={"User-Agent"},
        ) as session:
            # get the session id
            url = "/login/login.json"
            data = {
                "user[email]": self.enphase_username,
                "user[password]": self.enphase_password,
            }
            async with session.post(url, data=data) as r:
                session_id = (await r.json())["session_id"]

            # then get the jwt with the session id
            url = f"/entrez-auth-token?serial_num={self.enphase_serialno}"
            headers = {"Cookie": f"_enlighten_4_session={session_id}"}
            async with session.get(url, headers=headers) as r:
                data = await r.json()

        return {
            "fetched": datetime.fromtimestamp(data["generation_time"]),
            "expiry": datetime.fromtimestamp(data["expires_at"]),
            "token": data["token"],
        }
