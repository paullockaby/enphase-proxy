FROM python:3.13.3-slim-bookworm@sha256:21e39cf1815802d4c6f89a0d3a166cc67ce58f95b6d1639e68a394c99310d2e5 AS base

# github metadata
LABEL org.opencontainers.image.source=https://github.com/paullockaby/enphase-proxy

# install updates and dependencies
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -q update && apt-get -y upgrade && \
    apt-get install --no-install-recommends -y tini && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# used all over the place
ENV APP_NAME=enphase_proxy
ENV APP_ROOT=/opt/$APP_NAME

# create the user (do not use yet)
RUN groupadd -g 1000 app && useradd -u 1000 -g 1000 -d /home/app --create-home app

FROM base AS builder

# install dependencies -- need git to run dunamai
RUN apt-get -q update && apt-get install -y --no-install-recommends git

# now become the app user to set up poetry and the versioning tool
RUN pip3 install poetry>=2 dunamai --no-cache-dir && mkdir -p $APP_ROOT && chown 1000:1000 $APP_ROOT
COPY --chown=1000:1000 pyproject.toml poetry.lock LICENSE $APP_ROOT/

# we have enough to install the application now
USER app
WORKDIR $APP_ROOT
RUN touch $APP_ROOT/README.md && \
    poetry config virtualenvs.in-project true && \
    poetry config virtualenvs.create true && \
    poetry install --without=dev --no-interaction --no-directory --no-root

# get and set the version number of the application
RUN mkdir -p /tmp/src
COPY --chown=1000:1000 . /tmp/src/
RUN poetry version $(dunamai from git --dirty --path=/tmp/src)

# now copy over the application
COPY --chown=1000:1000 src $APP_ROOT/src/
RUN poetry install --without=dev --no-interaction

# now copy over the entrypoint
COPY --chown=1000:1000 entrypoint $APP_ROOT/
RUN chmod +x $APP_ROOT/entrypoint

FROM base AS final

# copy over our actual application
COPY --from=builder --chown=0:0 $APP_ROOT/entrypoint /entrypoint
COPY --from=builder --chown=0:0 $APP_ROOT/.venv $APP_ROOT/.venv
COPY --from=builder --chown=0:0 $APP_ROOT/src $APP_ROOT/src

# set up the virtual environment
ENV VIRTUALENV=$APP_ROOT/.venv
ENV PATH=$VIRTUALENV/bin:$PATH

# start application
USER app
ENTRYPOINT ["/entrypoint"]
