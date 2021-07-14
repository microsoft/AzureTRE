# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.166.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3, 3.9, 3.8, 3.7, 3.6
ARG VARIANT="3"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

# [Option] Install Node.js
ARG INSTALL_NODE="true"
ARG NODE_VERSION="lts/*"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# Install terraform
RUN apt-get update && apt-get install -y gnupg software-properties-common curl \
    && curl -fsSL https://apt.releases.hashicorp.com/gpg |  apt-key add - \
    && apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
    && apt-get update && apt-get install -y terraform

# Install Azure CLI
RUN apt-get update \
    && apt-get install ca-certificates curl apt-transport-https lsb-release gnupg \
    && curl -sL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor | tee /etc/apt/trusted.gpg.d/microsoft.gpg > /dev/null \
    && AZ_REPO=$(lsb_release -cs) \
    && echo "deb [arch=amd64] https://packages.microsoft.com/repos/azure-cli/ $AZ_REPO main" | tee /etc/apt/sources.list.d/azure-cli.list \
    && apt-get update && apt-get -y install azure-cli

# Make sure docker group id matches that on WSL.
RUN groupadd --gid 1001 docker

# Install Docker
RUN apt-get update &&  sudo apt-get install -y  apt-transport-https ca-certificates curl gnupg  lsb-release \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/debian $(lsb_release -cs) stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io

# Install nekos act - run GitHub workflows locally https://github.com/nektos/act
RUN curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Install Certbot
RUN apt-get install -y python3 python3-venv libaugeas0 \
    && python3 -m venv /opt/certbot/ \
    && /opt/certbot/bin/pip install --upgrade pip \
    && /opt/certbot/bin/pip install certbot

# Install Porter
RUN export PORTER_HOME=/home/vscode/.porter && curl -L https://cdn.porter.sh/latest/install-linux.sh | bash && /home/vscode/.porter/porter mixin install docker  && chown -R vscode /home/vscode/.porter/

ENV PATH /home/vscode/.porter/:$PATH

# Install Azure Function Core Tools
RUN curl https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > microsoft.gpg \
    && sudo mv microsoft.gpg /etc/apt/trusted.gpg.d/microsoft.gpg \
    && sudo sh -c 'echo "deb [arch=amd64] https://packages.microsoft.com/debian/$(lsb_release -rs | cut -d'.' -f 1)/prod $(lsb_release -cs) main" > /etc/apt/sources.list.d/dotnetdev.list' \
    && sudo apt-get update \
    && sudo apt-get update \
    && sudo apt-get install azure-functions-core-tools-3

# Install requirements
COPY ["requirements.txt", "requirements-dev.txt", "/tmp/pip-tmp/" ]
COPY ["management_api_app/requirements.txt", "/tmp/pip-tmp/management_api_app/" ]
COPY ["processor_function/requirements.txt", "/tmp/pip-tmp/processor_function/" ]
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt && rm -rf /tmp/pip-tmp

RUN usermod -a -G docker vscode

USER vscode
