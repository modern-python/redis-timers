FROM artifactory.raiffeisen.ru/python-community-docker/python:3.13.5-slim-rbru

ARG ARTIFACTORY_USER
ARG ARTIFACTORY_PASSWORD

ENV UV_DEFAULT_INDEX=https://$ARTIFACTORY_USER:$ARTIFACTORY_PASSWORD@artifactory.raiffeisen.ru/artifactory/api/pypi/remote-pypi/simple \
    UV_INDEX_RAIF_USERNAME=$ARTIFACTORY_USER \
    UV_INDEX_RAIF_PASSWORD=$ARTIFACTORY_PASSWORD \
    UV_INDEX_COMMUNITY_USERNAME=$ARTIFACTORY_USER \
    UV_INDEX_COMMUNITY_PASSWORD=$ARTIFACTORY_PASSWORD \
    UV_INDEX_TEAM_USERNAME=$ARTIFACTORY_USER \
    UV_INDEX_TEAM_PASSWORD=$ARTIFACTORY_PASSWORD \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_LINK_MODE=copy \
    UV_NO_MANAGED_PYTHON=1

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --all-extras --no-install-project

COPY . .
