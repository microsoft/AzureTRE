#!/bin/bash
WS_NAME=$1
WORKSPACE_RESOURCE_NAME_SUFFIX=$2
KEYVAULT_NAME=$3
ARM_CLIENT_ID=$4
ARM_SUBSCRIPTION_ID=$5

# Login using the Managed Identity
az login --identity -u "$ARM_CLIENT_ID"

# Get the name of the private-endpoint-connection
az network private-endpoint-connection list -g "$WS_NAME" -n "$KEYVAULT_NAME" --type Microsoft.Keyvault/vaults
name=$(az network private-endpoint-connection list \
  --id "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${WS_NAME}/providers/Microsoft.KeyVault/vaults/${KEYVAULT_NAME}" | \
  jq -r "[.[] | select(.properties.privateLinkServiceConnectionState.status == \"Pending\") | \
  select(.properties.privateEndpoint.id | endswith(\"${WORKSPACE_RESOURCE_NAME_SUFFIX}\"))] | first | .name")

# Exit if name not found
if [ -z "$name" ]; then
    echo "No pending private endpoint connection found."
    exit 1
fi

# Approve the private-endpoint-connection
az network private-endpoint-connection approve \
  -g "$WS_NAME" \
  -n "$name" \
  --resource-name "$KEYVAULT_NAME" \
  --type "Microsoft.KeyVault/vaults" \
  --description "Auto-Approved-Terraform"
