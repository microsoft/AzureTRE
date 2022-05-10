#!/bin/bash
set -e

# This script assumes you have created an .env from the sample and the variables
# will come from there.
# shellcheck disable=SC2154
export TF_VAR_docker_registry_server="$TF_VAR_acr_name.azurecr.io"
export TF_VAR_docker_registry_username=$TF_VAR_acr_name
TF_VAR_docker_registry_password=$(az acr credential show --name "${TF_VAR_acr_name}" --query passwords[0].value -o tsv | sed 's/"//g')
export TF_VAR_docker_registry_password

export TF_LOG=""

# This script assumes you have created an .env from the sample and the variables
# will come from there.
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
    -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
    -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
    -backend-config="key=tre-workspace-service-gitea-$TF_VAR_id"

terraform destroy -auto-approve
