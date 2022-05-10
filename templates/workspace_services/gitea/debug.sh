#!/bin/bash
set -e

# This script is not used and is left here for you to debug the creation of the workspace
# at a Terraform level without having to interact with Porter

# shellcheck disable=SC1091
. .env

# This script assumes you have created an .env from the sample and the variables
# will come from there.
# shellcheck disable=SC2154
terraform -chdir=terraform init -reconfigure -input=false -backend=true \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=tre-workspace-service-gitea-$TF_VAR_id"
terraform -chdir=terraform apply -auto-approve

read -p "Would you like to delete this terraform bundle? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 0
fi

terraform -chdir=terraform destroy -auto-approve
