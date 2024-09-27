#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Uncomment this line to see each command for debugging (careful: this will show secrets!)
#set -o xtrace

export TF_LOG="TRACE"
export TF_LOG_PATH="/home/adminuser/tf.log"

# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
    -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
    -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
    -backend-config="key=tre-workspace-service-gitea-${TF_VAR_id}"

terraform plan

terraform apply -auto-approve
