# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.166.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3, 3.9, 3.8, 3.7, 3.6
ARG VARIANT="3"
FROM mcr.microsoft.com/vscode/devcontainers/python:dev-${VARIANT}-buster

# [Option] Install Node.js
ARG INSTALL_NODE="true"
ARG NODE_VERSION="lts/*"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su vscode -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# Install terraform
ARG TERRAFORM_VERSION
RUN apt-get update && apt-get install -y gnupg software-properties-common curl \
    && curl -fsSL https://apt.releases.hashicorp.com/gpg | apt-key add - \
    && apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
    && apt-get update && apt-get install -y terraform "${TERRAFORM_VERSION}"

# Install Azure CLI
RUN curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# Make sure docker group id matches that on WSL.
RUN groupadd --gid 1001 docker

# Install Docker
RUN apt-get update && sudo apt-get install -y  apt-transport-https ca-certificates curl gnupg  lsb-release \
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
RUN export PORTER_HOME=/home/vscode/.porter \
    && curl -L https://cdn.porter.sh/latest/install-linux.sh | bash \
    && ${PORTER_HOME}/porter mixin install docker \
    && chown -R vscode ${PORTER_HOME}

ENV PATH /home/vscode/.porter/:$PATH

# Install requirements
COPY ["requirements.txt", "/tmp/pip-tmp/" ]
COPY ["api_app/requirements.txt", "api_app/requirements-dev.txt", "/tmp/pip-tmp/api_app/" ]
COPY ["resource_processor/vmss_porter/requirements.txt", "/tmp/pip-tmp/resource_processor/vmss_porter/" ]
COPY ["docs/requirements.txt", "/tmp/pip-tmp/docs/" ]
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt && rm -rf /tmp/pip-tmp

RUN usermod -a -G docker vscode

USER vscode
