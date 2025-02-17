#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset

# Uncomment for debugging (will show secrets)
# set -o xtrace

function usage() {
    cat <<USAGE
    Usage: $0 --resource-group some_rg --vault-name some_vault
    Options:
        --resource-group     The name of the Azure Resource Group containing the Recovery Services Vault.
        --vault-name         The name of the Recovery Services Vault.
    Environment Variables:
        AZURE_ENVIRONMENT    The name of the Azure environment (e.g., AzureCloud, AzureChinaCloud, etc.). Must be set.
USAGE
    exit 1
}

# Ensure required commands are available
for cmd in az jq; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: $cmd is not installed."
        exit 1
    fi
done

# Ensure environment variable is set
if [ -z "${AZURE_ENVIRONMENT:-}" ]; then
    echo "Error: AZURE_ENVIRONMENT environment variable is not set."
    usage
fi

# Ensure arguments are provided
if [ $# -eq 0 ]; then
    usage
fi

# Parse arguments
while [ "$1" != "" ]; do
    case $1 in
    --resource-group)
        shift
        RESOURCE_GROUP=$1
        ;;
    --vault-name)
        shift
        VAULT_NAME=$1
        ;;
    *)
        echo "Unexpected argument: '$1'"
        usage
        ;;
    esac

    if [[ -z "$2" ]]; then
        break
    fi

    shift
done

# Ensure required arguments are set
if [ -z "${RESOURCE_GROUP:-}" ] || [ -z "${VAULT_NAME:-}" ]; then
    echo "Error: --resource-group and --vault-name are required."
    usage
fi

# Set Azure Cloud environment
az cloud set --name "$AZURE_ENVIRONMENT"

# Check if Vault Exists
echo "Checking for Recovery Services Vault: $VAULT_NAME in $RESOURCE_GROUP"
vault_exists=$(az resource show --resource-group "$RESOURCE_GROUP" --name "$VAULT_NAME" --resource-type "Microsoft.RecoveryServices/vaults" --query "id" -o tsv || echo "")

if [ -z "$vault_exists" ]; then
    echo "Vault does not exist or is already deleted. Skipping cleanup."
    exit 0
fi

# **Disable Soft Delete for the Vault**
echo "Disabling soft delete for Recovery Services Vault..."
az backup vault backup-properties set --resource-group "$RESOURCE_GROUP" --vault-name "$VAULT_NAME" --soft-delete-feature-state Disable || echo "Warning: Unable to disable soft delete."

# **Verify Soft Delete is Disabled**
soft_delete_status=$(az backup vault backup-properties show --resource-group "$RESOURCE_GROUP" --vault-name "$VAULT_NAME" --query "softDeleteFeatureState" -o tsv)
if [[ "$soft_delete_status" != "Disabled" ]]; then
    echo "Error: Soft delete is still enabled. Vault cannot be deleted."
    exit 1
fi

# **Get all protected backup items (VMs, File Shares, SQL, etc.)**
echo "Fetching all protected backup items..."
protected_items=$(az backup item list --resource-group "$RESOURCE_GROUP" --vault-name "$VAULT_NAME" --query "[].{name:name, containerName:properties.containerName, type:properties.protectedItemType}" -o json)

# **Disable protection for each registered backup item**
for row in $(echo "$protected_items" | jq -c '.[]'); do
    item_name=$(echo "$row" | jq -r '.name')
    container_name=$(echo "$row" | jq -r '.containerName')
    item_type=$(echo "$row" | jq -r '.type')

    echo "Disabling protection for: $item_name ($item_type)"
    az backup protection disable --resource-group "$RESOURCE_GROUP" --vault-name "$VAULT_NAME" --container-name "$container_name" --item-name "$item_name" --delete-backup-data true --yes || echo "Warning: Failed to disable protection for $item_name"
done




