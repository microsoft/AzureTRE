#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
set -o xtrace

# Configure AzureRM provider to user Azure AD to connect to storage accounts
export ARM_STORAGE_USE_AZUREAD=true

# Configure AzureRM backend to user Azure AD to connect to storage accounts
export ARM_USE_AZUREAD=true
export ARM_USE_OIDC=true

# terraform_wrapper_path="../../devops/scripts/terraform_wrapper.sh"

# This variables are loaded in for us
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

echo "*** Migrating TF Resources... ***"
terraform show
terraform show -json
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

# Remove old NSG association resources
declare -a old_nsg_assoc_resources=(
  "module.network.azurerm_subnet_network_security_group_association.bastion"
  "module.network.azurerm_subnet_network_security_group_association.app_gw"
  "module.network.azurerm_subnet_network_security_group_association.shared"
  "module.network.azurerm_subnet_network_security_group_association.web_app"
  "module.network.azurerm_subnet_network_security_group_association.resource_processor"
  "module.network.azurerm_subnet_network_security_group_association.airlock_processor"
  "module.network.azurerm_subnet_network_security_group_association.airlock_notification"
  "module.network.azurerm_subnet_network_security_group_association.airlock_storage"
  "module.network.azurerm_subnet_network_security_group_association.airlock_events"
  "module.network.azurerm_subnet_network_security_group_association.firewall_management"
)

for resource in "${old_nsg_assoc_resources[@]}"; do
  if terraform state list | grep -q "$resource"; then
    echo "Removing NSG association resource: $resource"
    terraform state rm "$resource"
  else
    echo "NSG association resource not found in state: $resource"
  fi
done

# Remove old subnet resources
declare -a old_subnet_resources=(
  "module.network.azurerm_subnet.bastion"
  "module.network.azurerm_subnet.azure_firewall"
  "module.network.azurerm_subnet.app_gw"
  "module.network.azurerm_subnet.web_app"
  "module.network.azurerm_subnet.shared"
  "module.network.azurerm_subnet.resource_processor"
  "module.network.azurerm_subnet.airlock_processor"
  "module.network.azurerm_subnet.airlock_notification"
  "module.network.azurerm_subnet.airlock_storage"
  "module.network.azurerm_subnet.airlock_events"
  "module.network.azurerm_subnet.firewall_management"
)

for resource in "${old_subnet_resources[@]}"; do
  if terraform state list | grep -q "$resource"; then
    echo "Removing subnet resource: $resource"
    terraform state rm "$resource"
  else
    echo "Subnet resource not found in state: $resource"
  fi
done

# Remove the old Virtual Network resource
old_vnet_address="module.network.azurerm_virtual_network.core"
if terraform state list | grep -q "$old_vnet_address"; then
  # Retrieve the VNet ID from state
  vnet_id=$(terraform state show "$old_vnet_address" | awk '/^id/ {print $3}')
  echo "Removing VNet resource: $old_vnet_address (ID: $vnet_id)"
  terraform state rm "$old_vnet_address"
else
  echo "VNet resource not found in state: $old_vnet_address"
fi

# Re-import the Virtual Network using the new inline configuration.
# With the new configuration the VNet is now defined as "azurerm_virtual_network.core".
new_vnet_address="azurerm_virtual_network.core"
if [ -n "${vnet_id:-}" ]; then
  echo "Importing VNet with ID: $vnet_id into new resource address: $new_vnet_address"
  terraform import "$new_vnet_address" "$vnet_id"
else
  echo "No VNet ID found; skipping re-import of VNet."
fi

echo "*** Migration is done. ***"
