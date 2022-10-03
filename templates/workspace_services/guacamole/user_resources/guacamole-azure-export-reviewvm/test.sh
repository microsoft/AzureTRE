#!/bin/bash

AZURE_TRE_VERSION=0.4.3

curl -o azuretre.tar.gz -L "https://github.com/microsoft/AzureTRE/archive/refs/tags/v${AZURE_TRE_VERSION}.tar.gz" \
  && tar -xzf azuretre.tar.gz "AzureTRE-${AZURE_TRE_VERSION}/templates/workspace_services/guacamole/user_resources/guacamole-azure-windowsvm"  --strip-components=6 --skip-old-files \
  && rm -rf azuretre.tar.gz

# Apply patch with the difference from the base workspace
patch -p0 < ./windowsvm.diff


make terraform-deploy \
  DIR=templates/workspace_services/guacamole/user_resources/guacamole-azure-linuxvm/ TF_VAR_workspace_id=$WORKSPACE_ID TF_VAR_parent_service_id=$GUACAMOLE_SERVICE_ID TF_VAR_image="Ubuntu 18.04" TF_VAR_vm_size="2 CPU | 8GB RAM" TF_VAR_shared_storage_access=false TF_VAR_shared_storage_name=foo TF_VAR_tre_resource_id=0001
