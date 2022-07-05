#!/bin/bash

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
set -o xtrace


# Delete any existing VM Extensions befroe a VM gets deleted.
# This is needed to work around bug https://github.com/hashicorp/terraform-provider-azurerm/issues/6098

MGMT_RESOURCE_GROUP_NAME=$1
MGMT_STORAGE_ACCOUNT_NAME=$2
TF_STATE_CONTAINER_NAME=$3
ID=$4

pushd terraform

terraform init -input=false -backend=true \
    -backend-config="resource_group_name=${MGMT_RESOURCE_GROUP_NAME}" \
    -backend-config="storage_account_name=${MGMT_STORAGE_ACCOUNT_NAME}" \
    -backend-config="container_name=${TF_STATE_CONTAINER_NAME}" \
    -backend-config="key=${ID}"

tf_state_list="$(terraform state list)"
echo "${tf_state_list}" | grep "azurerm_virtual_machine_extension." | xargs terraform state rm

popd
