#!/bin/bash

# Version of TRE to use as reference
AZURE_TRE_VERSION="0.5.0"

# Download the reference template locally
# and unpack the templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm into local directory
# --strip-components=5 removes the leading components of path, leaving only what's inside guacamole-azure-windowsvm
curl -o azuretre.tar.gz -L "https://github.com/microsoft/AzureTRE/archive/refs/tags/v${AZURE_TRE_VERSION}.tar.gz" \
  && tar -xzf azuretre.tar.gz "AzureTRE-${AZURE_TRE_VERSION}/templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm"  --strip-components=5 \
  && rm -rf azuretre.tar.gz

# We don't want the empty.txt end up in the diff
mv terraform/empty.txt .

# Create a patch with the difference from windowsvm directory
diff -Naur guacamole-azure-windowsvm/terraform terraform > windowsvm.patch

# Remove the reference directory
rm -rf guacamole-azure-windowsvm/

# Restore terraform directory to the state it was in
rm -rf terraform
mkdir terraform
mv empty.txt terraform/


