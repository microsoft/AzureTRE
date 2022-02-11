#!/bin/bash

set -x

function showUsage() {
    cat <<USAGE

    ATTENTION:
    The purpose of this script is to achieve backwards compatibility for deployment of TRE,
    as some of the resources that were originally part of templates/core/terraform are now moved into their own Porter bundles.
    (See https://github.com/microsoft/AzureTRE/issues/1177)
    The intent is to remove the script once the clients have migrated.
    General use of Terraform state manipulation is not recommended.

    Usage: $0 [-g | --mgmt-resource-group-name ]  [-s | --mgmt-storage-account-name] [-n | --state-container-name] [-k | --key]

    Options:
        -g, --mgmt-resource-group-name      Management resource group name
        -s, --mgmt-storage-account-name     Management storage account name
        -n, --state-container-name          State container name
        -k, --key                           Terraform State Key
USAGE
    exit 1
}

# if no arguments are provided, return showUsage function
if [ $# -eq 0 ]; then
    showUsage # run showUsage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -g | --mgmt-resource-group-name)
        shift
        MGMT_RESOURCE_GROUP_NAME=$1
        ;;
    -s | --mgmt-storage-account-name)
        shift
        MGMT_STORAGE_ACCOUNT_NAME=$1
        ;;
    -n | --state-container-name)
        shift
        CONTAINER_NAME=$1
        ;;
    -k | --key)
        shift
        KEY=$1
        ;;
    *)
       showUsage
        ;;
    esac
    shift # remove the current value for `$1` and use the next
done


if [[ -z ${MGMT_RESOURCE_GROUP_NAME+x} ]]; then
    echo -e "No terraform state resource group name provided\n"
   showUsage
fi

if [[ -z ${MGMT_STORAGE_ACCOUNT_NAME+x} ]]; then
    echo -e "No terraform state storage account name provided\n"
   showUsage
fi

if [[ -z ${CONTAINER_NAME+x} ]]; then
    echo -e "No terraform state container name provided\n"
   showUsage
fi

if [[ -z ${KEY+x} ]]; then
    echo -e "No KEY provided\n"
   showUsage
fi

RESOURCE_GROUP_ID="rg-${TRE_ID}"

# Initialsie state for Terraform, login to az to look up resources
pushd /cnab/app/terraform
terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${MGMT_RESOURCE_GROUP_NAME}" \
    -backend-config="storage_account_name=${MGMT_STORAGE_ACCOUNT_NAME}" \
    -backend-config="container_name=${CONTAINER_NAME}" \
    -backend-config="key=${KEY}"
az login --service-principal --username ${ARM_CLIENT_ID} --password ${ARM_CLIENT_SECRET} --tenant ${ARM_TENANT_ID}

# Import a resource if it exists in Azure but doesn't exist in Terraform
function import_if_exists() {
  ADDRESS=$1
  ID=$2
  CMD=$3

  # Check if the resource exists in Terraform
  terraform state show ${ADDRESS}
  TF_RESOURCE_EXISTS=$?
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
    terraform import -var 'tre_id=${TRE_ID}' -var 'location=${LOCATION}' ${ADDRESS} ${ID}
  fi
}

import_if_exists azurerm_public_ip.fwpip "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/publicIPAddresses/pip-fw-${TRE_ID}"

import_if_exists azurerm_firewall.fw "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}" || echo "Resource already exists"

import_if_exists azurerm_management_lock.fw "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/providers/Microsoft.Authorization/locks/fw-${TRE_ID}"

import_if_exists azurerm_route_table.rt \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/routeTables/rt-${TRE_ID}"

import_if_exists azurerm_subnet_route_table_association.rt_shared_subnet_association \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/SharedSubnet"

import_if_exists azurerm_subnet_route_table_association.rt_web_app_subnet_association \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/WebAppSubnet"

import_if_exists azurerm_subnet_route_table_association.rt_resource_processor_subnet_association \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/virtualNetworks/vnet-${TRE_ID}/subnets/ResourceProcessorSubnet"

# Firewall rules
import_if_exists azurerm_firewall_application_rule_collection.resource_processor_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-resource_processor_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-resource_processor_subnet"

import_if_exists azurerm_firewall_application_rule_collection.web_app_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet"

import_if_exists azurerm_firewall_application_rule_collection.shared_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-shared_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-shared_subnet"

import_if_exists azurerm_firewall_network_rule_collection.resource_processor_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-resource_processor_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-resource_processor_subnet"

import_if_exists azurerm_firewall_network_rule_collection.general \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/general" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/general"

import_if_exists azurerm_firewall_network_rule_collection.web_app_subnet \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-web_app_subnet" \
  "az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/networkRuleCollections/nrc-web_app_subnet"

# Diagnostic settings
import_if_exists azurerm_monitor_diagnostic_setting.firewall \
  "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}|diagnostics-firewall-${TRE_ID}" \
  "az monitor diagnostic-settings show --resource /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/rg-${TRE_ID}/providers/microsoft.network/azureFirewalls/fw-${TRE_ID} --name diagnostics-firewall-${TRE_ID}"

popd
