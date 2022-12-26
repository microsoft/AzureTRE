# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.166.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3, 3.9, 3.8, 3.7, 3.6
ARG VARIANT="3.8"
FROM mcr.microsoft.com/vscode/devcontainers/python:dev-${VARIANT}-bullseye

# This will be set to true when running in VSCode
ARG INTERACTIVE="false"

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Set up non-root user
COPY .devcontainer/scripts/non-root-user.sh /tmp/
RUN bash /tmp/non-root-user.sh "${USERNAME}" "${USER_UID}" "${USER_GID}"

# Set env for tracking that we're running in a devcontainer
ENV DEVCONTAINER=true

# Install Node.js for GH actions tests and UI
ARG NODE_VERSION="lts/*"
RUN su $USERNAME -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"

# Install terraform
ARG TERRAFORM_VERSION="1.3.6"
COPY .devcontainer/scripts/terraform.sh /tmp/
RUN bash /tmp/terraform.sh "${TERRAFORM_VERSION}" /usr/bin

ARG DOCKER_GROUP_ID
COPY .devcontainer/scripts/docker-client.sh /tmp/
RUN /tmp/docker-client.sh $USERNAME

# Install Docker
RUN apt-get update && apt-get install -y ca-certificates curl gnupg lsb-release --no-install-recommends \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce="5:20.10.21~3-0~debian-bullseye" docker-ce-cli="5:20.10.21~3-0~debian-bullseye" containerd.io="1.6.12-1" --no-install-recommends \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Certbot
RUN if [ "${INTERACTIVE}" = "true" ]; then \
    apt-get update && apt-get install -y libaugeas0 --no-install-recommends \
    && python3 -m venv /opt/certbot/ \
    && /opt/certbot/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/certbot/bin/pip install --no-cache-dir certbot \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* ; fi

# Install Porter
# Not using the script from https://cdn.porter.sh/latest/install-linux.sh
# as it installs things we don't need and duplicates the binary.
# TODO: Remove Porter v0 https://github.com/microsoft/AzureTRE/issues/2990
ARG PORTER_MIRROR=https://cdn.porter.sh
ARG PORTER_VERSION=v0.38.13
ARG PORTER_TERRAFORM_MIXIN_VERSION=v1.0.0-rc.1
ARG PORTER_AZ_MIXIN_VERSION=v0.7.3
ARG PORTER_AZURE_PLUGIN_VERSION=v0.11.2
ARG PORTER_HOME_V0=/home/$USERNAME/.porter-v0/
COPY .devcontainer/scripts/porter.sh /tmp/
RUN if [ "${INTERACTIVE}" = "true" ]; then \
    export PORTER_MIRROR=${PORTER_MIRROR} \
    PORTER_VERSION=${PORTER_VERSION} \
    PORTER_TERRAFORM_MIXIN_VERSION=${PORTER_TERRAFORM_MIXIN_VERSION} \
    PORTER_AZ_MIXIN_VERSION=${PORTER_AZ_MIXIN_VERSION} \
    PORTER_AZURE_PLUGIN_VERSION=${PORTER_AZURE_PLUGIN_VERSION} \
    PORTER_HOME=${PORTER_HOME_V0} \
    && /tmp/porter.sh ; fi

# can't be in a non default path
# ARG PORTER_HOME_V1=/home/$USERNAME/.porter-v1/
ARG PORTER_HOME_V1=/home/$USERNAME/.porter/
ARG PORTER_VERSION=v1.0.4
ARG PORTER_TERRAFORM_MIXIN_VERSION=v1.0.0
ARG PORTER_AZ_MIXIN_VERSION=v1.0.0
ARG PORTER_AZURE_PLUGIN_VERSION=v1.0.1
COPY .devcontainer/scripts/porter-v1.sh /tmp/
RUN export PORTER_VERSION=${PORTER_VERSION} \
    PORTER_TERRAFORM_MIXIN_VERSION=${PORTER_TERRAFORM_MIXIN_VERSION} \
    PORTER_AZ_MIXIN_VERSION=${PORTER_AZ_MIXIN_VERSION} \
    PORTER_AZURE_PLUGIN_VERSION=${PORTER_AZURE_PLUGIN_VERSION} \
    PORTER_HOME=${PORTER_HOME_V1} \
    && /tmp/porter-v1.sh

ENV PATH ${PORTER_HOME_V1}:$PATH

# Install requirements
COPY ["requirements.txt", "/tmp/pip-tmp/" ]
COPY ["api_app/requirements.txt", "api_app/requirements-dev.txt", "/tmp/pip-tmp/api_app/" ]
COPY ["resource_processor/vmss_porter/requirements.txt", "/tmp/pip-tmp/resource_processor/vmss_porter/" ]
COPY ["docs/requirements.txt", "/tmp/pip-tmp/docs/"]
COPY ["e2e_tests/requirements.txt", "/tmp/pip-tmp/e2e_tests/"]
COPY ["airlock_processor/requirements.txt", "/tmp/pip-tmp/airlock_processor/"]
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt

# Install azure-cli
ARG AZURE_CLI_VERSION=2.37.0-1~bullseye
COPY .devcontainer/scripts/azure-cli.sh /tmp/
RUN export AZURE_CLI_VERSION=${AZURE_CLI_VERSION} \
    && /tmp/azure-cli.sh

ARG YQ_VERSION="v4.30.6"
RUN curl -L --fail -o /usr/local/bin/yq "https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/yq_linux_amd64" \
    && chmod +x /usr/local/bin/yq

ARG PAJV_VERSION="1.2.0"
RUN npm install -g pajv@${PAJV_VERSION}

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
