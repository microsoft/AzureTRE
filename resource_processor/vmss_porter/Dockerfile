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

# TODO: Remove porter v0 https://github.com/microsoft/AzureTRE/issues/2990
# Install Porter
ARG PORTER_MIRROR=https://cdn.porter.sh
ARG PORTER_VERSION=v0.38.13
ARG PORTER_TERRAFORM_MIXIN_VERSION=v1.0.0-rc.1
ARG PORTER_AZ_MIXIN_VERSION=v0.7.3
ARG PORTER_AZURE_PLUGIN_VERSION=v0.11.2
ARG PORTER_HOME=/root/.porter-v0/
COPY scripts/porter.sh /tmp/
RUN export PORTER_MIRROR=${PORTER_MIRROR} \
    PORTER_VERSION=${PORTER_VERSION} \
    PORTER_TERRAFORM_MIXIN_VERSION=${PORTER_TERRAFORM_MIXIN_VERSION} \
    PORTER_AZ_MIXIN_VERSION=${PORTER_AZ_MIXIN_VERSION} \
    PORTER_AZURE_PLUGIN_VERSION=${PORTER_AZURE_PLUGIN_VERSION} \
    PORTER_HOME=${PORTER_HOME} \
    && /tmp/porter.sh

ENV PORTER_HOME_V0 ${PORTER_HOME}

# can't be in a non default path
# ARG PORTER_HOME_V1=/home/$USERNAME/.porter-v1/
ARG PORTER_HOME_V1=/root/.porter/
ARG PORTER_VERSION=v1.1.1
ARG PORTER_TERRAFORM_MIXIN_VERSION=v1.0.3
ARG PORTER_AZ_MIXIN_VERSION=v1.0.2
ARG PORTER_AZURE_PLUGIN_VERSION=v1.2.3
COPY scripts/porter-v1.sh /tmp/
RUN export PORTER_VERSION=${PORTER_VERSION} \
    PORTER_TERRAFORM_MIXIN_VERSION=${PORTER_TERRAFORM_MIXIN_VERSION} \
    PORTER_AZ_MIXIN_VERSION=${PORTER_AZ_MIXIN_VERSION} \
    PORTER_AZURE_PLUGIN_VERSION=${PORTER_AZURE_PLUGIN_VERSION} \
    PORTER_HOME=${PORTER_HOME_V1} \
    && /tmp/porter-v1.sh

ENV PATH ${PORTER_HOME_V1}:$PATH

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

COPY ./vmss_porter/config.yaml ${PORTER_HOME_V1}/

ENV PYTHONPATH .

COPY ./vmss_porter/requirements.txt /tmp/
RUN pip3 --no-cache-dir install -r /tmp/requirements.txt

COPY . /app

WORKDIR /app/

EXPOSE 8080

CMD ["./run.sh"]
