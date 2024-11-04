#!/bin/bash
set -e

# This script is used to install the bundle directly without having to interact with Porter

# This script assumes you have created an .env from the sample and the variables
# will come from there.
# shellcheck disable=SC2154
terraform init -upgrade -reconfigure -input=false -backend=true \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TF_VAR_tre_id}-ws-${TF_VAR_tre_resource_id}"
