# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN rm -f /etc/apt/apt.conf.d/docker-clean; echo 'Binary::apt::APT::Keep-Downloaded-Packages "true";' > /etc/apt/apt.conf.d/keep-cache

# Install Azure CLI
ARG AZURE_CLI_VERSION=2.67.0-1~bookworm
COPY scripts/azure-cli.sh /tmp/
RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt \
    export AZURE_CLI_VERSION=${AZURE_CLI_VERSION} \
    && /tmp/azure-cli.sh



# Install Docker
ARG DOCKER_CE_VERSION="5:27.4.1-1~debian.12~bookworm"
ARG DOCKER_CE_CLI_VERSION="5:27.4.1-1~debian.12~bookworm"
ARG DOCKER_CONTAINERD_VERSION="1.7.24-1"
RUN --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/lib/apt \
    apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release --no-install-recommends \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce="$DOCKER_CE_VERSION" docker-ce-cli="$DOCKER_CE_CLI_VERSION" containerd.io="$DOCKER_CONTAINERD_VERSION" --no-install-recommends



ENV PYTHONPATH=.

COPY ./vmss_porter/requirements.txt /tmp/
RUN pip3 --no-cache-dir install -r /tmp/requirements.txt

COPY . /app

WORKDIR /app/

EXPOSE 8080

CMD ["./run.sh"]
