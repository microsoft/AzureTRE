#!/bin/bash
# See remove_state.sh for the purpose of these scripts
echo "IMPORTING STATE FOR FIREWALL..."

# check for the existence of the RG. If it's not there it's because we're in CI and building from scratch - we can skip this script
set +e
RESOURCE_GROUP_ID="rg-${TRE_ID}"
az group show -n $RESOURCE_GROUP_ID
if [ $? -ne 0 ]; then
  echo "RG not found, skipping import_state"
  exit 0
fi

set -e

# Initialise state for Terraform
terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}-shared-service-firewall"

# Import a resource if it exists in Azure but doesn't exist in Terraform
tf_state_list="$(terraform state list)"
function import_if_exists() {
  ADDRESS=$1
  ID=$2
  CMD=$3

  # Check if the resource exists in Terraform
  TF_RESOURCE_EXISTS=$(echo "$tf_state_list" | grep -q ^${ADDRESS}$; echo $?)

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
    terraform import -var "tre_id=${TRE_ID}" -var "location=${LOCATION}" ${ADDRESS} ${ID}
  fi
}

import_if_exists azurerm_firewall.fw "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}" || echo "Resource already exists"

# Firewall rules
import_if_exists azurerm_firewall_application_rule_collection.resource_processor_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-resource_processor_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-resource_processor_subnet"

import_if_exists azurerm_firewall_application_rule_collection.shared_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-shared_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-shared_subnet"

import_if_exists azurerm_firewall_application_rule_collection.web_app_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet"

import_if_exists azurerm_firewall_network_rule_collection.general \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/general" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/general"

import_if_exists azurerm_firewall_network_rule_collection.resource_processor_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-resource_processor_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-resource_processor_subnet"

import_if_exists azurerm_firewall_network_rule_collection.web_app_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-web_app_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-web_app_subnet"


# Diagnostic settings
import_if_exists azurerm_monitor_diagnostic_setting.firewall \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}|diagnostics-firewall-${TRE_ID}" \
  "az monitor diagnostic-settings show --resource /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/rg-${TRE_ID}/providers/microsoft.network/azureFirewalls/fw-${TRE_ID} --name diagnostics-firewall-${TRE_ID}"


import_if_exists azurerm_public_ip.fwpip "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/publicIPAddresses/pip-fw-${TRE_ID}"


import_if_exists azurerm_subnet_route_table_association.rt_web_app_subnet_association \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/WebAppSubnet"

# Route tables
import_if_exists azurerm_route_table.rt \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/routeTables/rt-${TRE_ID}"

import_if_exists azurerm_subnet_route_table_association.rt_shared_subnet_association \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/SharedSubnet"

import_if_exists azurerm_subnet_route_table_association.rt_resource_processor_subnet_association \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/ResourceProcessorSubnet"
