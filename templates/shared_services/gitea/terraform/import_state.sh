#!/bin/bash
# See remove_state.sh for the purpose of these scripts
echo "IMPORTING STATE FOR GITEA..."

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
    -backend-config="key=${TRE_ID}-shared-service-gitea"

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


import_if_exists azurerm_firewall_application_rule_collection.web_app_subnet_gitea \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet_gitea" \
"az network firewall show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/azureFirewalls/fw-${TRE_ID}/applicationRuleCollections/arc-web_app_subnet_gitea"

import_if_exists azurerm_user_assigned_identity.gitea_id \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/id-gitea-${TRE_ID}"

import_if_exists azurerm_app_service.gitea \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Web/sites/gitea-${TRE_ID}"

import_if_exists azurerm_private_endpoint.gitea_private_endpoint \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/privateEndpoints/pe-gitea-${TRE_ID}"

import_if_exists azurerm_app_service_virtual_network_swift_connection.gitea-integrated-vnet \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Web/sites/gitea-${TRE_ID}/config/virtualNetwork"

GITEA_PW_VALUE="$(az keyvault secret show --vault-name kv-${TRE_ID} -n gitea-${TRE_ID}-admin-password -o tsv --query value)"
terraform import random_password.gitea_password $GITEA_PW_VALUE

GITEA_PW_ID="$(az keyvault secret show --vault-name kv-${TRE_ID} -n gitea-${TRE_ID}-admin-password -o tsv --query id)"
import_if_exists azurerm_key_vault_secret.gitea_password \
"${GITEA_PW_ID}" \
"az keyvault secret show --id ${GITEA_PW_ID}"

import_if_exists azurerm_storage_share.gitea \
"https://stg${TRE_ID}.file.core.windows.net/gitea-data" \
"az resource show --ids /subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Storage/storageAccounts/stg${TRE_ID}/fileServices/default/shares/gitea-data"

import_if_exists azurerm_mysql_server.gitea \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.DBforMySQL/servers/mysql-${TRE_ID}"

import_if_exists azurerm_mysql_database.gitea \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.DBforMySQL/servers/mysql-${TRE_ID}/databases/gitea"

import_if_exists azurerm_private_endpoint.private-endpoint \
"/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_ID}/providers/Microsoft.Network/privateEndpoints/pe-mysql-${TRE_ID}"

DB_PW_VALUE="$(az keyvault secret show --vault-name kv-${TRE_ID} -n mysql-${TRE_ID}-password -o tsv --query value)"
terraform import random_password.password $DB_PW_VALUE

DB_PW_ID="$(az keyvault secret show --vault-name kv-${TRE_ID} -n mysql-${TRE_ID}-password -o tsv --query id)"
import_if_exists azurerm_key_vault_secret.db_password "${DB_PW_ID}" \
"az keyvault secret show --id ${DB_PW_ID}"
