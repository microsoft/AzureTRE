#!/bin/bash

AZURE_TRE_VERSION="0.4.3"

curl -o azuretre.tar.gz -L "https://github.com/microsoft/AzureTRE/archive/refs/tags/v${AZURE_TRE_VERSION}.tar.gz" \
  && tar -xzf azuretre.tar.gz "AzureTRE-${AZURE_TRE_VERSION}/templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm"  --strip-components=6 --skip-old-files \
  && rm -rf azuretre.tar.gz

patch -p0 < ./windowsvm.diff
