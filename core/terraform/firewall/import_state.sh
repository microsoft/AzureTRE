#!/bin/bash
# shellcheck disable=SC2154

# See remove_state.sh for the purpose of these scripts
echo "IMPORTING STATE FOR FIREWALL..."

# check for the existence of the RG. If it's not there it's because we're in CI and building from scratch - we can skip this script
set +e
RESOURCE_GROUP_ID="rg-${TRE_ID}"
if ! az group show -n "$RESOURCE_GROUP_ID"; then
  echo "RG not found, skipping import_state"
  exit 0
fi

set -e

# shellcheck disable=SC1091
source "$(dirname "$0")/../../../devops/scripts/mgmtstorage_enable_public_access.sh"

# Initialise state for Terraform
terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

# Import a resource if it exists in Azure but doesn't exist in Terraform
tf_state_list="$(terraform state list)"
function import_if_exists() {
  ADDRESS=$1
  ID=$2
  CMD=$3

  # Check if the resource exists in Terraform
  echo "Checking if ${ADDRESS} exists in Terraform state..."
  ESCAPED_ADDRESS=$(printf '%q' "${ADDRESS}")
  TF_RESOURCE_EXISTS=$(echo "$tf_state_list" | grep -q ^"${ESCAPED_ADDRESS}"$; echo $?)

  if [[ ${TF_RESOURCE_EXISTS} -eq 0 ]]; then
    echo "${ADDRESS} already in TF State, ignoring..."
    return
  fi

  # Some resources, e.g. Firewall rules and Diagnostics, don't show up in `az resource show`,
  # so we need a way to set up a custom command for them
  if [[ -z ${CMD} ]]; then
    CMD="az resource show --ids ${ID}"
  fi
  ${CMD} > /dev/null
  AZ_RESOURCE_EXISTS=$?



  # If resource exists in Terraform, it's already managed -- don't do anything
  # If resource doesn't exist in Terraform and doesn't exist in Azure, it will be created -- don't do anything
  # If resource doesn't exist in Terraform but exist in Azure, we need to import it
  if [[ ${TF_RESOURCE_EXISTS} -ne 0 && ${AZ_RESOURCE_EXISTS} -eq 0 ]]; then
    echo "IMPORTING ${ADDRESS} ${ID}"
    terraform import -var "tre_id=${TRE_ID}" -var "location=${LOCATION}" "${ADDRESS}" "${ID}"
  fi
}

# Firewall
import_if_exists module.firewall.azurerm_firewall.fw "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}"

# Firewall IPs
if [[ "${FIREWALL_SKU}" == "Basic" ]]; then
  import_if_exists module.firewall.azurerm_public_ip.fwmanagement[0] "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/publicIPAddresses/pip-fw-management-${TRE_ID}"
fi

import_if_exists module.firewall.azurerm_public_ip.fwtransit[0] "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/publicIPAddresses/pip-fw-${TRE_ID}"

# Firewall policy
import_if_exists module.firewall.azurerm_firewall_policy.root "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/firewallPolicies/fw-policy-${TRE_ID}"
import_if_exists module.firewall.azurerm_firewall_policy_rule_collection_group.core \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/firewallPolicies/fw-policy-${TRE_ID}/ruleCollectionGroups/rcg-core"


# Diagnostic settings
import_if_exists module.firewall.azurerm_monitor_diagnostic_setting.firewall \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}|diagnostics-fw-${TRE_ID}" \
  "az monitor diagnostic-settings show --resource /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/rg-${TRE_ID}/providers/microsoft.network/azureFirewalls/fw-${TRE_ID} --name diagnostics-fw-${TRE_ID}"

# Route tables
import_if_exists azurerm_route_table.rt \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/routeTables/rt-${TRE_ID}"

# import_if_exists azurerm_subnet_route_table_association.rt_shared_subnet_association \
#   "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/SharedSubnet"

# import_if_exists azurerm_subnet_route_table_association.rt_resource_processor_subnet_association \
#   "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/ResourceProcessorSubnet"

# import_if_exists azurerm_subnet_route_table_association.rt_web_app_subnet_association \
#   "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/WebAppSubnet"

# import_if_exists azurerm_subnet_route_table_association.rt_airlock_processor_subnet_association \
#   "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/AirlockProcessorSubnet"

# import_if_exists azurerm_subnet_route_table_association.rt_airlock_storage_subnet_association \
#   "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/AirlockStorageSubnet"

# import_if_exists azurerm_subnet_route_table_association.rt_airlock_events_subnet_association \
#   "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/AirlockEventsSubnet"
