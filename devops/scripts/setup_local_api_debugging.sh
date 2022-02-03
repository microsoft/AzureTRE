#!/bin/bash
set -e

: ${TRE_ID?"You have not set you TRE_ID in ./templates/core/.env"}
: ${RESOURCE_GROUP_NAME?"Check RESOURCE_GROUP_NAME is defined in ./templates/core/tre.env"}
: ${SERVICE_BUS_RESOURCE_ID?"Check SERVICE_BUS_RESOURCE_ID is defined in ./templates/core/tre.env"}
: ${STATE_STORE_RESOURCE_ID?"Check STATE_STORE_RESOURCE_ID is defined in ./templates/core/tre.env"}
: ${COSMOSDB_ACCOUNT_NAME?"Check COSMOSDB_ACCOUNT_NAME is defined in ./templates/core/tre.env"}

export SERVICE_BUS_NAMESPACE="sb-${TRE_ID}"
IPADDR=$(curl ipecho.net/plain; echo)

echo "Adding local IP Address to ${COSMOSDB_ACCOUNT_NAME}. This may take a while . . . "
az cosmosdb update \
  --name ${COSMOSDB_ACCOUNT_NAME} \
  --resource-group ${RESOURCE_GROUP_NAME} \
  --ip-range-filter ${IPADDR}

echo "Adding local IP Address to ${SERVICE_BUS_NAMESPACE}."
az servicebus namespace network-rule add \
  --resource-group ${RESOURCE_GROUP_NAME} \
  --namespace-name ${SERVICE_BUS_NAMESPACE} \
  --ip-address ${IPADDR} \
  --action Allow

SERVICE_PRINCIPAL_SECRET=$(az ad sp create-for-rbac --name "${TRE_ID}_debug_spn" -o json)
export SERVICE_PRINCIPAL_ID=$(echo "$SERVICE_PRINCIPAL_SECRET" | jq -r '.appId')
export SERVICE_PRINCIPAL_SECRET=$(echo "$SERVICE_PRINCIPAL_SECRET" | jq -r '.password')

az role assignment create \
    --role "Azure Service Bus Data Sender" \
    --assignee ${SERVICE_PRINCIPAL_ID} \
    --scope ${SERVICE_BUS_RESOURCE_ID}

az role assignment create \
    --role "Azure Service Bus Data Receiver" \
    --assignee ${SERVICE_PRINCIPAL_ID} \
    --scope ${SERVICE_BUS_RESOURCE_ID}

az role assignment create \
    --role "Contributor" \
    --assignee ${SERVICE_PRINCIPAL_ID} \
    --scope ${STATE_STORE_RESOURCE_ID}

echo "Adding secrets to /workspaces/AzureTRE/templates/core/tre.env"
echo "AZURE_CLIENT_ID=${SERVICE_PRINCIPAL_ID}" >> ./templates/core/tre.env
echo "AZURE_CLIENT_SECRET=${SERVICE_PRINCIPAL_SECRET}" >> ./templates/core/tre.env
