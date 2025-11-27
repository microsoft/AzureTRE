#!/bin/bash
set -e

# shellcheck disable=SC1091
# shellcheck disable=SC2154
source ../../devops/scripts/storage_enable_public_access.sh \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}"

if [ ! -f ../tre_output.json ] || [ ! -s ../tre_output.json ]; then
  # Connect to the remote backend of Terraform
  export TF_LOG=""
  # shellcheck disable=SC2154
  terraform init -input=false -backend=true -reconfigure \
      -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
      -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
      -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
      -backend-config="key=${TRE_ID}"

  # Convert the output to json
  terraform output -json > ../tre_output.json
fi

# Now create an .env file
./json-to-env.sh < ../tre_output.json > ../private.env

# Pull in the core templates environment variables so we can build up new key/value pairs
if [ -f ../.env ]; then
  # shellcheck disable=SC1091
  source ../.env
fi

# These next ones from Check Dependencies
echo "SUBSCRIPTION_ID='${SUB_ID}'" >> ../private.env
echo "AZURE_SUBSCRIPTION_ID='${SUB_ID}'" >> ../private.env
echo "AZURE_TENANT_ID='${TENANT_ID}'" >> ../private.env
