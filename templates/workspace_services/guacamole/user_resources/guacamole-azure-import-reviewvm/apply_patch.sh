#!/bin/bash

# Version of TRE to use as reference
AZURE_TRE_VERSION="0.5.0"

# Download the repository of the AZURE_TRE_VERSION locally
# and unpack the templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm into local directory
# --strip-components=6 removes the leading components of path, leaving only what's inside guacamole-azure-windowsvm
# --skip-old-files keeps the files we already have in current directory
curl -o azuretre.tar.gz -L "https://github.com/microsoft/AzureTRE/archive/refs/tags/v${AZURE_TRE_VERSION}.tar.gz" \
  && tar -xzf azuretre.tar.gz "AzureTRE-${AZURE_TRE_VERSION}/templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm"  --strip-components=6 --skip-old-files \
  && rm -rf azuretre.tar.gz

# Apply patch which is the difference of this template with the guacamole-azure-windowsvm reference template
patch -p0 < ./windowsvm.patch
