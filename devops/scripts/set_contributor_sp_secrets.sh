#!/bin/bash
set -e

# This script adds the client (app) ID and the client secret (app password) of the service principal used for deploying
# resources (workspaces and workspace services) to Key Vault.
#
# Running the script requires that Azure CLI login has been done with the credentials that have privileges to access
# the Key Vault.
#
# Required environment variables:
#
#   - TRE_ID - The TRE ID, used to deduce the Key Vault name
#   - ARM_SUBSCRIPTION_ID - The Azure subscription ID
#   - RESOURCE_PROCESSOR_CLIENT_ID - The client ID of the service principal
#   - RESOURCE_PROCESSOR_CLIENT_SECRET - The client secret of the service principal
#

echo -e "\n\e[34m»»» 🤖 \e[96mCreating (or updating) service principal ID and secret to Key Vault\e[0m..."
key_vault_name="kv-$TRE_ID"
az account set --subscription $ARM_SUBSCRIPTION_ID
az keyvault secret set --name deployment-processor-azure-client-id --vault-name $key_vault_name --value $RESOURCE_PROCESSOR_CLIENT_ID
az keyvault secret set --name deployment-processor-azure-client-secret --vault-name $key_vault_name --value $RESOURCE_PROCESSOR_CLIENT_SECRET > /dev/null
