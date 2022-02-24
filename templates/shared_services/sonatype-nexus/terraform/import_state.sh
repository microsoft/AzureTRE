#!/bin/bash
# See remove_state.sh for the purpose of these scripts
echo "IMPORTING STATE FOR NEXUS..."

# check for the existence of the RG. If it's not there it's because we're in CI and building from scratch - we can skip this script
set +e
RESOURCE_GROUP_ID="rg-${TRE_ID}"
az group show -n $RESOURCE_GROUP_ID
if [ $? -ne 0 ]; then
  echo "RG not found, skipping import_state"
  exit 0
fi

set -e

# Initialsie state for Terraform
terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}-shared-service-sonatype-nexus"

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
  ${CMD}
  AZ_RESOURCE_EXISTS=$?

  # If resource exists in Terraform, it's already managed -- don't do anything
  # If resource doesn't exist in Terraform and doesn't exist in Azure, it will be created -- don't do anything
  # If resource doesn't exist in Terraform but exist in Azure, we need to import it
  if [[ ${TF_RESOURCE_EXISTS} -ne 0 && ${AZ_RESOURCE_EXISTS} -eq 0 ]]; then
    echo "IMPORTING ${ADDRESS} ${ID}"
    terraform import -var "tre_id=${TRE_ID}" -var "location=${LOCATION}" ${ADDRESS} ${ID}
  fi
}

import_if_exists azurerm_storage_share.nexus \
"https://stg${TRE_ID}.file.core.windows.net/nexus-data" \
"az resource show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Storage/storageAccounts/stg${TRE_ID}/fileServices/default/shares/nexus-data"

import_if_exists azurerm_app_service.nexus \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Web/sites/nexus-${TRE_ID}"

import_if_exists azurerm_firewall_application_rule_collection.web_app_subnet_nexus \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet_nexus" \
"az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet_nexus"

import_if_exists azurerm_private_endpoint.nexus_private_endpoint \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/privateEndpoints/pe-nexus-${TRE_ID}"

import_if_exists azurerm_app_service_virtual_network_swift_connection.nexus-integrated-vnet \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Web/sites/nexus-${TRE_ID}/config/virtualNetwork"

