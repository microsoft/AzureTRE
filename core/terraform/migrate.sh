#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# shellcheck disable=SC1091
source ../../devops/scripts/mgmtstorage_add_network_exception.sh

get_resource_id() {
  local json_data="$1"
  local resource_addr="$2"
  echo "$json_data" | jq -r --arg addr "$resource_addr" '
    def walk_resources:
      (.resources[]?),
      (.child_modules[]? | walk_resources);
    .values.root_module | walk_resources | select(.address==$addr) | .values.id
  '
}

# Configure AzureRM provider to use Azure AD to connect to storage accounts
export ARM_STORAGE_USE_AZUREAD=true

# Configure AzureRM backend to use Azure AD to connect to storage accounts
export ARM_USE_AZUREAD=true
export ARM_USE_OIDC=true

# These variables are loaded in for us
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

echo "*** Migrating TF Resources... ***"

terraform refresh

# get TF state in JSON
terraform_show_json=$(terraform show -json)

# List of resource addresses to remove.
declare -a RESOURCES_TO_REMOVE=(
  "module.network.azurerm_subnet_network_security_group_association.bastion"
  "module.network.azurerm_subnet_network_security_group_association.app_gw"
  "module.network.azurerm_subnet_network_security_group_association.shared"
  "module.network.azurerm_subnet_network_security_group_association.web_app"
  "module.network.azurerm_subnet_network_security_group_association.resource_processor"
  "module.network.azurerm_subnet_network_security_group_association.airlock_processor"
  "module.network.azurerm_subnet_network_security_group_association.airlock_notification"
  "module.network.azurerm_subnet_network_security_group_association.airlock_storage"
  "module.network.azurerm_subnet_network_security_group_association.airlock_events"
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
vnet_address="module.network.azurerm_virtual_network.core"

# Check if migration is needed
migration_needed=0
for resource in "${RESOURCES_TO_REMOVE[@]}"; do
  resource_id=$(get_resource_id "${terraform_show_json}" "$resource")
  if [ -n "$resource_id" ] && [ "$resource_id" != "null" ]; then
    migration_needed=1
    break
  fi
done

# Remove old resources
if [ "$migration_needed" -eq 1 ]; then
  for resource in "${RESOURCES_TO_REMOVE[@]}"; do
    resource_id=$(get_resource_id "${terraform_show_json}" "$resource")
    if [ -n "$resource_id" ] && [ "$resource_id" != "null" ]; then
      terraform state rm "$resource"
    else
      echo "Resource that was supposed to be removed not found in state: ${resource}"
    fi
  done

  # Remove and re-import the VNet
  vnet_address="module.network.azurerm_virtual_network.core"
  vnet_id=$(get_resource_id "${terraform_show_json}" "$vnet_address" "vnet")
  if [ -n "${vnet_id}" ] && [ "${vnet_id}" != "null" ]; then
    terraform state rm "${vnet_address}"
    terraform import "${vnet_address}" "${vnet_id}"
  else
    echo "VNet resource not found in state: ${vnet_address}"
  fi
  echo "*** Migration Done ***"
else
  echo "No old resources found in the state, skipping migration."
  echo "*** Migration Skipped ***"
fi
