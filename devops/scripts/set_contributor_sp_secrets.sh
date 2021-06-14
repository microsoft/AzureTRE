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
#   - TF_VAR_tre_id - The TRE ID, used to deduce the Key Vault name
#   - SUB_ID - The Azure subscription ID
#   - CONTRIBUTOR_SP_CLIENT_ID - The client ID of the service principal
#   - CONTRIBUTOR_SP_CLIENT_SECRET - The client secret of the service principal
#

echo -e "\n\e[34m»»» 🤖 \e[96mCreating (or updating) service principal ID and secret to Key Vault\e[0m..."
key_vault_name="kv-$TF_VAR_tre_id"
az account set --subscription $SUB_ID
az keyvault secret set --name deployment-processor-azure-client-id --vault-name $key_vault_name --value $CONTRIBUTOR_SP_CLIENT_ID
az keyvault secret set --name deployment-processor-azure-client-secret --vault-name $key_vault_name --value $CONTRIBUTOR_SP_CLIENT_SECRET > /dev/null
