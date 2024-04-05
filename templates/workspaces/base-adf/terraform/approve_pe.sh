#!/bin/bash

# Log commands and exit on errors
set -ex

# Assuming command line arguments for simplicity
WS_NAME=$1
STORAGE_NAME=$2
WORKSPACE_RESOURCE_NAME_SUFFIX=$3
ARM_CLIENT_ID=$4
ARM_SUBSCRIPTION_ID=$5

# Login using the Managed Identity
az login --identity -u "$ARM_CLIENT_ID"

# Get the name of the private-endpoint-connection
name=$(az network private-endpoint-connection list \
  --id "/subscriptions/${ARM_SUBSCRIPTION_ID}/resourceGroups/${WS_NAME}/providers/Microsoft.Storage/storageAccounts/${STORAGE_NAME}" | \
  jq -r "[.[] | select(.properties.privateLinkServiceConnectionState.status == \"Pending\") | \
  select(.properties.privateEndpoint.id | endswith(\"pe-adf-ws-${WORKSPACE_RESOURCE_NAME_SUFFIX}\"))] | first | .name")

# Exit if name not found
if [ -z "$name" ]; then
    echo "No pending private endpoint connection found."
    exit 1
fi

# Approve the private-endpoint-connection
az network private-endpoint-connection approve \
  -g "$WS_NAME" \
  -n "$name" \
  --resource-name "$STORAGE_NAME" \
  --type "Microsoft.Storage/storageAccounts" \
  --description "Auto-Approved-Terraform"
