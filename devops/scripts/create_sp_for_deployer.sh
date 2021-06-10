#!/bin/bash
set -e

# This script creates a service principal, for deploying resources (workspaces and workspace services), and adds its
# client (app) ID and client secret (app password) to Key Vault. Running the script requires that Azure CLI login has
# been done with the credentials that allow creation of the service principal and have privileges to access the Key Vault.
#
# If a service principal already exists, the client secret gets changed but the ID will remain the same.
#
# Required environment variables set before running this script are:
#
#   - SUB_ID - Azure subscription ID
#   - TF_VAR_tre_id - TRE ID, used to construct the name of the Key Vault
#   - DEPLOYMENT_PROCESSOR_SERVICE_PRINCIPAL_NAME - The name for the service principal
#

echo -e "\n\e[34m»»» 🤖 \e[96mCreating service principal\e[0m..."
az account set --subscription $SUB_ID

# Scope defaults to the root of the current subscription. e.g., /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333
az_output=`az ad sp create-for-rbac --name $DEPLOYMENT_PROCESSOR_SERVICE_PRINCIPAL_NAME --role Contributor --sdk-auth`

client_id=`echo "$az_output" | jq -r '.clientId'`
client_secret=`echo "$az_output" | jq -r '.clientSecret'`

echo -e "\n\e[34m»»» 🤖 \e[96mCreating (or updating) service principal ID and secret to Key Vault\e[0m..."
key_vault_name="kv-$TF_VAR_tre_id"
az keyvault secret set --name deployment-processor-azure-client-id --vault-name $key_vault_name --value $client_id
az keyvault secret set --name deployment-processor-azure-client-secret --vault-name $key_vault_name --value $client_secret > /dev/null
