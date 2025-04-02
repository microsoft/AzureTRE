# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.166.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3.11 3.12, 3.13
ARG VARIANT="3.12"
ARG TARGETPLATFORM="linux/amd64"
FROM --platform="${TARGETPLATFORM}" mcr.microsoft.com/vscode/devcontainers/python:dev-${VARIANT}-bookworm

# This will be set to true when running in VSCode
ARG INTERACTIVE="false"

ARG USER_UID=1000
ARG USERNAME=vscode

# make user ID match user ID on host machine
RUN usermod --uid $USER_UID $USERNAME

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Set env for tracking that we're running in a devcontainer
ENV DEVCONTAINER=true

# Install Node.js for GH actions tests and UI
ARG NODE_VERSION="lts/*"
RUN su $USERNAME -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"

# Install terraform
ARG TERRAFORM_VERSION="1.9.8"
COPY .devcontainer/scripts/terraform.sh /tmp/
RUN bash /tmp/terraform.sh "${TERRAFORM_VERSION}" /usr/bin

ARG DOCKER_GROUP_ID
COPY .devcontainer/scripts/docker-client.sh /tmp/
RUN /tmp/docker-client.sh $USERNAME

# Install Docker
ARG DOCKER_CE_VERSION="5:27.4.1-1~debian.12~bookworm"
ARG DOCKER_CE_CLI_VERSION="5:27.4.1-1~debian.12~bookworm"
ARG DOCKER_COMPOSE_PLUGIN_VERSION="2.32.1-1~debian.12~bookworm"
ARG DOCKER_CONTAINERD_VERSION="1.7.24-1"
RUN apt-get update && apt-get install -y ca-certificates curl gnupg lsb-release --no-install-recommends \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce="$DOCKER_CE_VERSION" docker-ce-cli="$DOCKER_CE_CLI_VERSION" docker-compose-plugin="$DOCKER_COMPOSE_PLUGIN_VERSION" containerd.io="$DOCKER_CONTAINERD_VERSION" docker-buildx-plugin --no-install-recommends \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Certbot
RUN if [ "${INTERACTIVE}" = "true" ]; then \
    apt-get update && apt-get install -y libaugeas0 --no-install-recommends \
    && python3 -m venv /opt/certbot/ \
    && /opt/certbot/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/certbot/bin/pip install --no-cache-dir certbot \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* ; fi

# Install Porter, updates should be propagated to the RP.
ARG PORTER_HOME_V1=/home/$USERNAME/.porter/
ARG PORTER_VERSION=v1.2.1
ARG PORTER_TERRAFORM_MIXIN_VERSION=v1.0.5
ARG PORTER_AZ_MIXIN_VERSION=v1.0.4
ARG PORTER_AZURE_PLUGIN_VERSION=v1.2.3
COPY .devcontainer/scripts/porter-v1.sh /tmp/
RUN export PORTER_VERSION=${PORTER_VERSION} \
    PORTER_TERRAFORM_MIXIN_VERSION=${PORTER_TERRAFORM_MIXIN_VERSION} \
    PORTER_AZ_MIXIN_VERSION=${PORTER_AZ_MIXIN_VERSION} \
    PORTER_AZURE_PLUGIN_VERSION=${PORTER_AZURE_PLUGIN_VERSION} \
    PORTER_HOME=${PORTER_HOME_V1} \
    && /tmp/porter-v1.sh

ENV PATH ${PORTER_HOME_V1}:$PATH

# Install requirements
ARG PIP_VERSION=23.3.1
RUN  pip3 --no-cache-dir install pip==${PIP_VERSION} && pip3 config set global.disable-pip-version-check true
COPY ["requirements.txt", "/tmp/pip-tmp/" ]
COPY ["api_app/requirements.txt", "api_app/requirements-dev.txt", "/tmp/pip-tmp/api_app/" ]
COPY ["resource_processor/vmss_porter/requirements.txt", "/tmp/pip-tmp/resource_processor/vmss_porter/" ]
COPY ["docs/requirements.txt", "/tmp/pip-tmp/docs/"]
COPY ["e2e_tests/requirements.txt", "/tmp/pip-tmp/e2e_tests/"]
COPY ["airlock_processor/requirements.txt", "/tmp/pip-tmp/airlock_processor/"]
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt

# Install azure-cli
ARG AZURE_CLI_VERSION=2.67.0-1~bookworm
COPY .devcontainer/scripts/azure-cli.sh /tmp/
RUN export AZURE_CLI_VERSION=${AZURE_CLI_VERSION} \
    && /tmp/azure-cli.sh

ARG YQ_VERSION="v4.44.6"
RUN curl -L --fail -o /usr/local/bin/yq "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
    && chmod +x /usr/local/bin/yq

ARG PAJV_VERSION="1.2.0"
RUN npm install -g pajv@${PAJV_VERSION}

# Install git - required for terraform's git modules
RUN if [ "${INTERACTIVE}" = "false" ]; then \
apt-get update && apt-get install --no-install-recommends -y git \
&& apt-get clean -y && rm -rf /var/lib/apt/lists/* ; fi

USER $USERNAME

# Save command line history
RUN echo "export HISTFILE=$HOME/commandhistory/.bash_history" >> "$HOME/.bashrc" \
    && echo "export PROMPT_COMMAND='history -a'" >> "$HOME/.bashrc" \
    && mkdir -p "$HOME/commandhistory" \
    && touch "$HOME/commandhistory/.bash_history"

# Install github-cli
COPY ./.devcontainer/scripts/gh.sh /tmp/
RUN if [ "${INTERACTIVE}" = "true" ]; then /tmp/gh.sh; fi

# Install tre-cli
COPY ./cli /tmp/cli
WORKDIR /tmp/cli
RUN make install-cli && echo -e "\n# Set up tre completion\nsource <(_TRE_COMPLETE=bash_source tre)" >> ~/.bashrc

# Build x86-64 docker images by default
ENV DOCKER_DEFAULT_PLATFORM=amd64
