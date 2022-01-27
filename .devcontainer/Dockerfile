# See here for image contents: https://github.com/microsoft/vscode-dev-containers/tree/v0.166.1/containers/python-3/.devcontainer/base.Dockerfile

# [Choice] Python version: 3, 3.9, 3.8, 3.7, 3.6
ARG VARIANT="3.8"
FROM mcr.microsoft.com/vscode/devcontainers/python:dev-${VARIANT}-buster

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Set up non-root user
COPY .devcontainer/scripts/non-root-user.sh /tmp/
RUN bash /tmp/non-root-user.sh "${USERNAME}" "${USER_UID}" "${USER_GID}"

# Set env for tracking that we're running in a devcontainer
ENV DEVCONTAINER=true

# [Option] Install Node.js
ARG INSTALL_NODE="false"
ARG NODE_VERSION="lts/*"
RUN if [ "${INSTALL_NODE}" = "true" ]; then su $USERNAME -c "umask 0002 && . /usr/local/share/nvm/nvm.sh && nvm install ${NODE_VERSION} 2>&1"; fi

# Install terraform
ARG TERRAFORM_VERSION="1.0.5"
COPY .devcontainer/scripts/terraform.sh /tmp/
RUN bash /tmp/terraform.sh "${TERRAFORM_VERSION}" /usr/bin

ARG DOCKER_GROUP_ID
COPY .devcontainer/scripts/docker-client.sh /tmp/
RUN /tmp/docker-client.sh $USERNAME

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
RUN export PORTER_HOME=/home/$USERNAME/.porter \
    && curl -L https://cdn.porter.sh/latest/install-linux.sh | bash \
    && ${PORTER_HOME}/porter mixin install docker \
    && chown -R $USERNAME ${PORTER_HOME}

ENV PATH /home/$USERNAME/.porter/:$PATH

# Install requirements
COPY ["requirements.txt", "/tmp/pip-tmp/" ]
COPY ["api_app/requirements.txt", "api_app/requirements-dev.txt", "/tmp/pip-tmp/api_app/" ]
COPY ["resource_processor/vmss_porter/requirements.txt", "/tmp/pip-tmp/resource_processor/vmss_porter/" ]
COPY ["docs/requirements.txt", "/tmp/pip-tmp/docs/"]
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt && rm -rf /tmp/pip-tmp

# Install azure-cli
COPY ./.devcontainer/scripts/azure-cli.sh /tmp/
RUN /tmp/azure-cli.sh

RUN wget -O /usr/local/bin/yq https://github.com/mikefarah/yq/releases/download/v4.13.0/yq_linux_amd64 \
  && chmod +x /usr/local/bin/yq

USER $USERNAME
