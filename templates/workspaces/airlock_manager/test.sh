#!/bin/bash

AZURE_TRE_VERSION="0.4.2"

# apt-get update \
#   && apt-get install --no-install-recommends jq ca-certificates curl patch -y \
#   && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# WORKDIR $BUNDLE_DIR

# Copy all files from base workspace (note: some of them will be overwritten with the following COPY command)
curl -o azuretre.tar.gz -L "https://github.com/microsoft/AzureTRE/archive/refs/tags/v${AZURE_TRE_VERSION}.tar.gz" \
  && tar -xzf azuretre.tar.gz "AzureTRE-${AZURE_TRE_VERSION}/templates/workspaces/base"  --strip-components=4 --skip-old-files \
  && rm -rf azuretre.tar.gz

echo DOWNLOADED

patch -p0 < ./workspace_base.diff
