FROM python:3.12.8-slim-bookworm@sha256:2b0079146a74e23bf4ae8f6a28e1b484c6292f6fb904cbb51825b4a19812fcd8 AS base

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
RUN pip3 install poetry dunamai --no-cache-dir && mkdir -p $APP_ROOT && chown 1000:1000 $APP_ROOT
COPY --chown=1000:1000 pyproject.toml poetry.lock entrypoint $APP_ROOT/
RUN chmod +x $APP_ROOT/entrypoint

# we have enough to install the application now
USER app
WORKDIR $APP_ROOT
RUN poetry config virtualenvs.in-project true && \
    poetry config virtualenvs.create true && \
    poetry install --without=dev --no-interaction --no-directory --no-root

# update the version number of our application
COPY --chown=1000:1000 .git/ $APP_ROOT/.git
RUN poetry version $(dunamai from git --dirty)

# now copy over the application
COPY --chown=1000:1000 src $APP_ROOT/src/
RUN poetry install --without=dev --no-interaction

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
