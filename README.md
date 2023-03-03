# enphase-proxy
An application for proxying requests to a local Enphase Envoy system. This implements the new authentication mechanism that version D7.x.x enforces.

## Development

This library uses [Python Poetry](https://python-poetry.org/) for builds, tests, and deployment. Once you've installed Poetry you can install this project's dependencies with this command:

```
poetry install
```

Assuming that you have set up your environment as described later in this document, you can test the application by running this command:

```
poetry run python3 -m enphase_proxy
```

Still assuming that your environment is configured, an alternative way to run this is with `gunicorn`, like this:

```
poetry run gunicorn \
    --chdir=src \
    --worker-class=uvicorn.workers.UvicornWorker \
    --bind=127.0.0.1:8080 \
    --log-config=configurations/logging.conf \
    enphase_proxy.asgi:app
```

Still a third way to run this program is with Docker, like this:

```
docker build -t enphase_proxy .
docker run --rm \
    -p 8080:8080 \
    -e ENPHASE_LOCAL_API_URL=$ENPHASE_LOCAL_API_URL \
    -e ENPHASE_REMOTE_API_USERNAME=$ENPHASE_REMOTE_API_USERNAME \
    -e ENPHASE_REMOTE_API_PASSWORD=$ENPHASE_REMOTE_API_PASSWORD \
    -e ENPHASE_REMOTE_API_SERIALNO=$ENPHASE_REMOTE_API_SERIALNO \
    -e ENPHASE_REMOTE_API_URL=$ENPHASE_REMOTE_API_URL \
    enphase_proxy --bind=:8080 \
    --log-config=configurations/logging.conf \
    --worker-class=uvicorn.workers.UvicornWorker
```

## Configuration

Before you run the application you need to either (1) modify a configuration file called `src/configurations/development.conf` directory using the example or (2) add these environment variables to your development environment using something like direnv:

### `ENPHASE_LOCAL_API_URL`

The full URL to your local Enphase Envoy. This might be something like `https://192.168.1.200/` or `https://envoy.local/`.

### `ENPHASE_REMOTE_API_USERNAME`

The username that you use when you log in to [the Enphase portal](http://enlighten.enphaseenergy.com). This is going to be an email address.

### `ENPHASE_REMOTE_API_PASSWORD`

The username that you use when you log in to [the Enphase portal](http://enlighten.enphaseenergy.com).


### `ENPHASE_REMOTE_API_SERIALNO`

The serial number of your Enphase Envoy. You can find this within the Enphase portal on the "Devices" page and will be called "Gateway" or "IQ Gateway".

### `ENPHASE_REMOTE_API_URL`

The URL to use for programmatically logging in to the Enphase portal. This should probably be `https://enlighten.enphaseenergy.com/`.

### `ENPHASE_LOCAL_API_JWT`

If you set all of the environment variables defined above the `enphase-proxy` will, at startup and then periodically thereafter, hit the Enphase Enlighten system and get a new JWT. If you're testing then you might worry that you may be blocked. If you manage to get a valid JWT then set it here and the `enphase-proxy` tool will never hit the cloud. Since the JWTs (currently) are set with six _month_ lifetimes, this is pretty safe to do.

## Manually Getting the JWT

Above it is mentioned that you can hardcode a JWT to avoid hitting the Enphase Enlighten API. How do you do that?

First, get this information:

```
export ENPHASE_USERNAME=your-enphase.com-username@whatever.com
export ENPHASE_PASSWORD=your-enphase.com-password
export ENPHASE_SERIALNO=your-enphase-envoy-serial-number
```

Second, run this command to get a valid session id:

```
curl https://enlighten.enphaseenergy.com/login/login.json \
   -d "user[email]=${ENPHASE_USERNAME}&user[password]=${ENPHASE_PASSWORD}" \
   | jq -r '.session_id'
```

Third, put the session id that you got from the previous command into this command and run this to get the JWT:

```
curl "https://enlighten.enphaseenergy.com/entrez-auth-token?serial_num=${ENPHASE_SERIALNO}" \
  -H "cookie: _enlighten_4_session=XXXXXyour-session-idXXXXXX"
```

Of course, the Enphase folks have not published any of this. All of this information was gleaned off of various forums -- mostly HomeAssistant forums. It may change and break at any time.

## Trademarks

Enphase(R), Envoy(R) are trademarks of Enphase Energy(R).

All trademarks are the property of their respective owners.

Any trademarks used in this project are used in a purely descriptive manner and to state compatability.
