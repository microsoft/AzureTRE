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

# Get the object id of the currently logged in user
LOGGED_IN_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv)

# Assign Role Permissions.
az role assignment create \
    --role "Azure Service Bus Data Sender" \
    --assignee ${LOGGED_IN_OBJECT_ID} \
    --scope ${SERVICE_BUS_RESOURCE_ID}

az role assignment create \
    --role "Azure Service Bus Data Receiver" \
    --assignee ${LOGGED_IN_OBJECT_ID} \
    --scope ${SERVICE_BUS_RESOURCE_ID}

az role assignment create \
    --role "Contributor" \
    --assignee ${LOGGED_IN_OBJECT_ID} \
    --scope ${STATE_STORE_RESOURCE_ID}
