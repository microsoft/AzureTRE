#!/bin/bash
set -e

if [ ! -f ../tre_output.json ]; then
  # Connect to the remote backend of Terraform
  export TF_LOG=""
  terraform init -input=false -backend=true -reconfigure -upgrade \
      -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
      -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
      -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
      -backend-config="key=${TRE_ID}"

  # Convert the output to json
  terraform output -json > ../tre_output.json
fi

# Now create an .env file
./json-to-env.sh < ../tre_output.json > ../tre.env

# Add a few extra values to the file to help us (i.e. for local debugging api_app and resource processor)
echo "SERVICE_BUS_FULLY_QUALIFIED_NAMESPACE=sb-${TRE_ID}.servicebus.windows.net" >> ../tre.env
echo "REGISTRY_SERVER=${TF_VAR_docker_registry_server}" >> ../tre.env
echo "MGMT_RESOURCE_GROUP_NAME=${TF_VAR_mgmt_resource_group_name}" >> ../tre.env
echo "MGMT_STORAGE_ACCOUNT_NAME=${TF_VAR_mgmt_storage_account_name}" >> ../tre.env
echo "TERRAFORM_STATE_CONTAINER_NAME=${TF_VAR_terraform_state_container_name}" >> ../tre.env
# These next ones from Check Dependencies
echo "SUBSCRIPTION_ID=${SUB_ID}" >> ../tre.env
echo "AZURE_SUBSCRIPTION_ID=${SUB_ID}" >> ../tre.env
echo "AZURE_TENANT_ID=${TENANT_ID}" >> ../tre.env
