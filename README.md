# enphase-proxy

An application for proxying requests to a local Enphase Envoy system. This implements the new authentication mechanism that version D7.x.x enforces.

![GitHub License](https://img.shields.io/github/license/paullockaby/enphase-proxy)
![GitHub Release](https://img.shields.io/github/v/release/paullockaby/enphase-proxy)
![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2Fpaullockaby%2Fenphase-proxy%2Fmain%2Fpyproject.toml)
[![Merge Pipelines](https://github.com/paullockaby/enphase-proxy/actions/workflows/merge.yaml/badge.svg)](https://github.com/paullockaby/enphase-proxy/actions/workflows/merge.yaml)

[![Mastodon Follow](https://img.shields.io/mastodon/follow/106882571030731815?domain=https%3A%2F%2Funcontrollablegas.com)](https://uncontrollablegas.com/@paul)

## Table of contents

* [Introduction](#introduction)
* [Quick start](#quick-start)
* [Usage](#usage)
* [Known issues and limitations](#known-issues-and-limitations)
* [Getting help](#getting-help)
* [Contributing](#contributing)
* [License](#license)
* [Acknowledgments](#acknowledgments)

## Introduction

The Enphase Envoy system has an API that you can use to get information from your solar panels. However, it uses a JWT that is issued by Enphase and expires after some duration. If you want to query the Enphase Envoy device without having to worry about keeping track of this token then this proxy is your ticket. It handles all of that and you can just query this proxy without thinking about tokens or passwords or whatever.

## Quick start

This library uses [Python Poetry](https://python-poetry.org/) for builds, tests, and deployment. Once you've installed Poetry you can install this project's dependencies with this command:

```
poetry install
```

Assuming that you have set up your environment as described later in this document, you can test the application by running this command:

```
poetry run python3 -m enphase_proxy
```

Still assuming that your environment is configured, an alternative way to run this is with `hypercorn`, like this:

```
poetry run hypercorn \
    --bind=127.0.0.1:8080 \
    --access-logfile=- \
    --error-logfile=- \
    --worker-class=uvloop \
    enphase_proxy.asgi:app
```

Still a third way to run this program is with Docker, like this:

```
docker build -t enphase_proxy .

# using the login mechanism
docker run --rm \
    -p 8080:8080 \
    -e ENPHASE_LOCAL_API_URL=$ENPHASE_LOCAL_API_URL \
    -e ENPHASE_REMOTE_API_USERNAME=$ENPHASE_REMOTE_API_USERNAME \
    -e ENPHASE_REMOTE_API_PASSWORD=$ENPHASE_REMOTE_API_PASSWORD \
    -e ENPHASE_REMOTE_API_SERIALNO=$ENPHASE_REMOTE_API_SERIALNO \
    -e ENPHASE_REMOTE_API_URL=$ENPHASE_REMOTE_API_URL \
    enphase_proxy \
    --bind=:8080 \
    --access-logfile=- \
    --error-logfile=- \
    --worker-class=uvloop

# or using an existing token
docker run --rm \
    -p 8080:8080 \
    -e ENPHASE_LOCAL_API_URL=$ENPHASE_LOCAL_API_URL \
    -e ENPHASE_LOCAL_API_JWT=$ENPHASE_LOCAL_API_JWT \
    enphase_proxy \
    --bind=:8080 \
    --access-logfile=- \
    --error-logfile=- \
    --worker-class=uvloop
```

### Testing the API

Once you've got it running you can test it with `curl`, like this:

```
curl -X POST http://localhost:8080/production.json | jq
```

### Configuration

Before you run the application you need to either (1) modify or create a configuration file in the `src/configurations` directory using the example or (2) add these environment variables to your development environment using something like `direnv`:

* `ENVIRONMENT` -- The name of the "environment" to use. Roughly this defines which configuration file to use in the `src/configurations` directory. That is, if you set this to `development` then the proxy will load `development.conf`.
* `ENPHASE_LOCAL_API_URL` -- The full URL to your local Enphase Envoy. This might be something like `https://192.168.1.200/` or `https://envoy.local/`.
* `ENPHASE_REMOTE_API_USERNAME` -- The username that you use when you log in to [the Enphase portal](http://enlighten.enphaseenergy.com). This is going to be an email address.
* `ENPHASE_REMOTE_API_PASSWORD` -- The username that you use when you log in to [the Enphase portal](http://enlighten.enphaseenergy.com).
* `ENPHASE_REMOTE_API_SERIALNO` -- The serial number of your Enphase Envoy. You can find this within the Enphase portal on the "Devices" page and will be called "Gateway" or "IQ Gateway".
* `ENPHASE_REMOTE_API_URL` -- The URL to use for programmatically logging in to the Enphase portal. This should probably be `https://enlighten.enphaseenergy.com/`.
* `ENPHASE_LOCAL_API_JWT` -- If you set all the environment variables defined above the `enphase-proxy` will, at startup and then periodically thereafter, hit the Enphase Enlighten system and get a new JWT. If you're testing then you might worry that you may be blocked. If you have to get a valid JWT on hand then set it here and the `enphase-proxy` tool will never hit the cloud. Since the JWTs (currently) are set with six _month_ lifetimes, this is pretty safe to do for a time period. If this environment variable is set then all of the `ENPHASE_REMOTE_` environment variables are ignored.

### Manually getting a JWT

Above it is mentioned that you can hardcode a JWT to avoid hitting the Enphase Enlighten API. How do you do that?

First, get this information:

```
export ENPHASE_REMOTE_API_USERNAME=your-enphase.com-username@whatever.com
export ENPHASE_REMOTE_API_PASSWORD=your-enphase.com-password
export ENPHASE_REMOTE_API_SERIALNO=your-enphase-envoy-serial-number
```

Second, run this command to get a valid session id:

```
curl https://enlighten.enphaseenergy.com/login/login.json \
   -d "user[email]=${ENPHASE_REMOTE_API_USERNAME}&user[password]=${ENPHASE_REMOTE_API_PASSWORD}" \
   | jq -r '.session_id'
```

Third, put the session id that you got from the previous command into this command and run this to get the JWT:

```
curl "https://enlighten.enphaseenergy.com/entrez-auth-token?serial_num=${ENPHASE_REMOTE_API_SERIALNO}" \
  -H "cookie: _enlighten_4_session=XXXXXyour-session-idXXXXXX" \
  | jq -r '.token'
```

Once you have the JWT in hand you can run queries like this:

```
curl -k -H "Authorization: Bearer XXXyour-jwt-tokenXXX" https://envoy.local/production.json
```

Of course, the Enphase folks have not published any of this. All of this information was gleaned off of various forums -- mostly HomeAssistant forums. It may change and break at any time.

## Usage

See [Installation](#installation).

## Known issues and limitations

There are no known issues or limitations at this time.

## Getting help

Please use GitHub Issues to raise bugs or feature requests or to otherwise communicate with the project. For more details on how to get help, please read the [contributing](#contributing) section.

## Contributing

This project welcomes contributions! Please be cognizant of the [code of conduct](CODE_OF_CONDUCT.md) when interacting with or contributing to this project. You may contribute in many ways:

* By filing bug reports. Please use GitHub Issues to submit any bugs that you may encounter.
* By filing feature requests. Be aware that we may not implement every feature request but we will evaluate them and provide feedback.
* By submitting pull requests. Please use GitHub to submit pull requests.
* By writing documentation. If you see something that could be explained better or is not explained at all, please submit a pull request to update the documentation. Alternatively, just submit an issue describing what is unclear and how it could be more clear and we will endeavor to update the documentation.

If you choose to submit a pull request please follow these guidelines:

* Please provide a clean, concise title for your pull request and a clear description of what you are changing so that it may be evaluated more effectively.
* Limit any pull request to a single change or the minimum number of changes necessary to achieve the feature or bug fix. Many smaller pull requests are preferred over fewer, larger pull requests.
* No pull request will be reviewed unless and until the linter and the tests pass. You can the linter and the tests locally and we encourage you to do so.
* Not every change can or may be accepted. If you are uncertain whether your pull request would be accepted then please open an issue before beginning work to discuss what you would like to do.
* This project is licensed using the Apache License and that by submitting code you accept that your code will be licensed the same.

Again, please use GitHub Issues and GitHub Pull Requests to communicate with the project. It is the fastest and most effective way to be heard.

If you have security feedback you can reach out to [contact@paullockaby.com](mailto:contact@paullockaby.com) to raise your security finding in a confidential manner so that we may provide a fix when the vulnerability is made public. If you are not sure that your feedback is security related please err on the side of caution and send the email. The worst that will happen is you will be asked to create a GitHub Issue.

## License

Copyright &copy; 2023-2024 Paul Lockaby. All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0)

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.

## Acknowledgements

Enphase(R), Envoy(R) are trademarks of Enphase Energy(R).

All trademarks are the property of their respective owners.

Any trademarks used in this project are used in a purely descriptive manner and to state compatability.
