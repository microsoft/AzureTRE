#!/bin/bash
set -e

export TF_LOG=""
terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
    -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
    -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
    -backend-config="key=${TF_VAR_tre_id}"

export RESOURCE_GROUP=$(terraform output -raw core_resource_group_name)
export APPLICATION_GATEWAY=$(terraform output -raw app_gateway_name)
export STORAGE_ACCOUNT=$(terraform output -raw static_web_storage)
export KEYVAULT=$(terraform output -raw keyvault_name)
export FQDN=$(terraform output -raw azure_tre_fqdn)

echo "RESOURCE_GROUP=${RESOURCE_GROUP}"
echo "APPLICATION_GATEWAY=${APPLICATION_GATEWAY}"
echo "STORAGE_ACCOUNT=${STORAGE_ACCOUNT}"
echo "KEYVAULT=${KEYVAULT}"
echo "FQDN=${FQDN}"
