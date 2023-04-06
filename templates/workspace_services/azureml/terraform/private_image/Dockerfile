# https://github.com/Azure/AzureML-Containers/blob/master/base/cpu/openmpi4.1.0-ubuntu22.04/Dockerfile

# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
FROM mcr.microsoft.com/azureml/openmpi4.1.0-ubuntu22.04

ARG TRE_ID
ARG TRE_LOCATION
ENV NEXUS_PROXY_URL="https://nexus-${TRE_ID}.${TRE_LOCATION}.cloudapp.azure.com"

# Set Nexus Conda
ENV PATH="/anaconda/condabin":$PATH
ENV PATH="/anaconda/bin":$PATH
ENV PATH="/anaconda/envs/py38_default/bin":$PATH

RUN conda config --add channels "${NEXUS_PROXY_URL}/repository/conda-mirror/main/"  --system && \
  conda config --add channels "${NEXUS_PROXY_URL}/repository/conda-repo/main/"  --system && \
  conda config --remove channels defaults --system && \
  conda config --set channel_alias "${NEXUS_PROXY_URL}/repository/conda-mirror/"  --system

# Set PyPi sources
RUN printf "[global]\nindex = ${NEXUS_PROXY_URL}/repository/pypi/pypi\nindex-url = ${NEXUS_PROXY_URL}/repository/pypi/simple\ntrusted-host = ${NEXUS_PROXY_URL}\n" >> /etc/pip.conf
