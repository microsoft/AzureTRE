#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# Configure AzureRM provider to user Azure AD to connect to storage accounts
export ARM_STORAGE_USE_AZUREAD=true

# Configure AzureRM backend to user Azure AD to connect to storage accounts
export ARM_USE_AZUREAD=true
export ARM_USE_OIDC=true

terraform_wrapper_path="../../devops/scripts/terraform_wrapper.sh"

# This variables are loaded in for us
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

echo "*** Migrating TF Resources... ***"


terraform_show_json=$(terraform show -json)

# Remove cnab-state legacy state path form state. Needs to be run before refresh, as refresh will fail.
state_store_legacy_path=$(echo "${terraform_show_json}" \
   | jq 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_storage_share.storage_state_path") | .values.id')

if [ -n "${state_store_legacy_path}" ]; then
  echo -e "\n\e[96mRemoving legacy state path from TF state\e[0m..."
  terraform state rm azurerm_storage_share.storage_state_path
fi

# terraform show might fail if provider schema has changed. Since we don't call apply at this stage a refresh is needed
terraform refresh

# 1. Check we have a root_module in state
# 2. Grab the Resource ID
# 3. Delete the old resource from state
# 4. Import the new resource type in using the existing Azure Resource ID

terraform_show_json=$(terraform show -json)

# example migration
# # azurerm_app_service_plan -> azurerm_service_plan
# core_app_service_plan_id=$(echo "${terraform_show_json}" \
#   | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_app_service_plan.core") | .values.id')
# if [ -n "${core_app_service_plan_id}" ]; then
#   echo "Migrating ${core_app_service_plan_id}"
#   terraform state rm azurerm_app_service_plan.core
#   if [[ $(az resource list --query "[?id=='${core_app_service_plan_id}'] | length(@)") == 0 ]];
#   then
#     echo "The resource doesn't exist on Azure. Skipping importing it back to state."
#   else
#     terraform import azurerm_service_plan.core "${core_app_service_plan_id}"
#   fi
# fi

echo "*** Migration is done. ***"
