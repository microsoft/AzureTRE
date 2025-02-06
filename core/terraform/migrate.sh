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

# This variables are loaded in for us
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

echo "*** Migrating TF Resources... ***"

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

# List of NSG association resource addresses to remove.
declare -a NSG_ASSOC_RESOURCES=(
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

echo "*** Removing NSG Associations ***"

for resource in "${NSG_ASSOC_RESOURCES[@]}"; do
  resource_id=$(echo "${terraform_show_json}" | jq -r --arg addr "$resource" '
    def walk_resources:
      (.resources[]? ),
      (.child_modules[]? | walk_resources);
    .values.root_module | walk_resources | select(.address==$addr) | .values.id
  ')

  if [ -n "$resource_id" ] && [ "$resource_id" != "null" ]; then
    echo "Removing NSG association: ${resource} (id: ${resource_id})"
    terraform state rm "$resource"
  else
    echo "NSG association resource not found in state: ${resource}"
  fi
done

### Step 2: Remove Old Subnets
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

echo "*** Removing Subnets ***"
for resource in "${old_subnet_resources[@]}"; do
  resource_id=$(echo "${terraform_show_json}" | jq -r --arg addr "$resource" '
    def walk_resources:
      (.resources[]? ),
      (.child_modules[]? | walk_resources);
    .values.root_module | walk_resources | select(.address==$addr) | .values.id
  ')

  if [ -n "$resource_id" ] && [ "$resource_id" != "null" ]; then
    echo "Removing subnet: ${resource} (id: ${resource_id})"
    terraform state rm "$resource"
  else
    echo "Subnet resource not found in state: ${resource}"
  fi
done

### Step 3: Remove Old Virtual Network
echo "*** Removing VNet ***"
vnet_address="module.network.azurerm_virtual_network.core"
vnet_id=$(echo "${terraform_show_json}" | jq -r --arg addr "$vnet_address" '
  def walk_resources:
    (.values.root_module.resources[]?),
    (.values.root_module.child_modules[]? | .resources[]?);
  walk_resources | select(.address == $addr) | .values.id
')

if [ -n "${vnet_id}" ] && [ "${vnet_id}" != "null" ]; then
  echo "Removing VNet from state: ${vnet_address} (ID: ${vnet_id})"
  terraform state rm "${vnet_address}"
else
  echo "VNet resource not found in state: ${vnet_address}"
fi


### Step 4: Re-import Virtual Network
echo "*** Re-importing VNet ***"
if [ -n "${vnet_id}" ] && [ "${vnet_id}" != "null" ]; then
  echo "Importing VNet with ID: ${vnet_id} into new resource address: ${vnet_address}"
  terraform import "${vnet_address}" "${vnet_id}"
else
  echo "No VNet ID found; skipping re-import of VNet."
fi


### Step 5: Remove Old Private Endpoints
echo "*** Removing Private Endpoints ***"

declare -a PRIVATE_ENDPOINTS=(
  "azurerm_private_endpoint.api_private_endpoint"
  "azurerm_private_endpoint.blobpe"
  "azurerm_private_endpoint.filepe"
  "azurerm_private_endpoint.kvpe"
  "azurerm_private_endpoint.mongo"
  "azurerm_private_endpoint.sbpe"
  "azurerm_private_endpoint.sspe"
)

for resource in "${PRIVATE_ENDPOINTS[@]}"; do
  resource_id=$(echo "${terraform_show_json}" | jq -r --arg addr "$resource" '
    def walk_resources:
      (.resources[]? ),
      (.child_modules[]? | walk_resources);
    .values.root_module | walk_resources | select(.address==$addr) | .values.id
  ')

  if [ -n "$resource_id" ] && [ "$resource_id" != "null" ]; then
    echo "Removing Private Endpoint: ${resource} (id: ${resource_id})"
    terraform state rm "$resource"
  else
    echo "Private Endpoint resource not found in state: ${resource}"
  fi
done

### Step 6: Re-importing Private Endpoints
echo "*** Re-importing Private Endpoints ***"

for resource in "${PRIVATE_ENDPOINTS[@]}"; do
  resource_id=$(echo "${terraform_show_json}" | jq -r --arg addr "$resource" '
    def walk_resources:
      (.resources[]? ),
      (.child_modules[]? | walk_resources);
    .values.root_module | walk_resources | select(.address==$addr) | .values.id
  ')

  if [ -n "$resource_id" ] && [ "$resource_id" != "null" ]; then
    echo "Re-importing Private Endpoint: ${resource} (id: ${resource_id})"
    terraform import "$resource" "$resource_id"
  else
    echo "No Private Endpoint ID found for ${resource}, skipping import."
  fi
done
