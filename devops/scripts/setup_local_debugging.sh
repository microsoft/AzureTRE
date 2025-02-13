#!/bin/bash
set -e

private_env_path="./core/private.env"

: "${TRE_ID?"You have not set your TRE_ID in ./config_yaml"}"
: "${RESOURCE_GROUP_NAME?"Check RESOURCE_GROUP_NAME is defined in ${private_env_path}"}"
: "${SERVICE_BUS_RESOURCE_ID?"Check SERVICE_BUS_RESOURCE_ID is defined in ${private_env_path}"}"
: "${STATE_STORE_RESOURCE_ID?"Check STATE_STORE_RESOURCE_ID is defined in ${private_env_path}"}"
: "${COSMOSDB_MONGO_RESOURCE_ID?"Check COSMOSDB_MONGO_RESOURCE_ID is defined in ${private_env_path}"}"
: "${COSMOSDB_ACCOUNT_NAME?"Check COSMOSDB_ACCOUNT_NAME is defined in ${private_env_path}"}"
: "${COSMOSDB_MONGO_ACCOUNT_NAME?"Check COSMOSDB_MONGO_ACCOUNT_NAME is defined in ${private_env_path}"}"
: "${AZURE_SUBSCRIPTION_ID?"Check AZURE_SUBSCRIPTION_ID is defined in ${private_env_path}"}"
: "${EVENT_GRID_STATUS_CHANGED_TOPIC_RESOURCE_ID?"Check EVENT_GRID_STATUS_CHANGED_TOPIC_RESOURCE_ID is defined in ${private_env_path}"}"
: "${EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_RESOURCE_ID?"Check EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_RESOURCE_ID is defined in ${private_env_path}"}"
: "${KEYVAULT_URI?"Check KEYVAULT_URI is defined in ${private_env_path}"}"
: "${KEYVAULT?"Check KEYVAULT is defined in ${private_env_path}"}"
: "${KEYVAULT_RESOURCE_ID?"Check KEYVAULT_RESOURCE_ID is defined in ${private_env_path}"}"

set -o pipefail
set -o nounset
# set -o xtrace

SERVICE_BUS_NAMESPACE="sb-${TRE_ID}"

if [[ -z ${PUBLIC_DEPLOYMENT_IP_ADDRESS:-} ]]; then
  IPADDR=$(curl ipecho.net/plain; echo)
else
  IPADDR=${PUBLIC_DEPLOYMENT_IP_ADDRESS}
fi

echo "Adding local IP Address to ${COSMOSDB_ACCOUNT_NAME}. This may take a while . . . "
az cosmosdb update \
  --name "${COSMOSDB_ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --ip-range-filter "${IPADDR}"

echo "Adding local IP Address to ${COSMOSDB_MONGO_ACCOUNT_NAME}. This may take a while . . . "
az cosmosdb update \
  --name "${COSMOSDB_MONGO_ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --ip-range-filter "${IPADDR}"

echo "Adding local IP Address to ${SERVICE_BUS_NAMESPACE}."
if az servicebus namespace network-rule-set list \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --namespace-name "${SERVICE_BUS_NAMESPACE}" \
  -o json | grep -q "${IPADDR}" ; then
  echo "IP Address ${IPADDR} already exists in ${SERVICE_BUS_NAMESPACE}. Skipping..."
else
  az servicebus namespace network-rule-set ip-rule add \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --namespace-name "${SERVICE_BUS_NAMESPACE}" \
    --ip-rule ip-address="${IPADDR}" action=Allow
fi

echo "Adding local IP Address to Event Grid Topics."
az eventgrid topic update \
  --public-network-access enabled \
  --inbound-ip-rules "${IPADDR}" allow \
  --ids "${EVENT_GRID_STATUS_CHANGED_TOPIC_RESOURCE_ID}" "${EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_RESOURCE_ID}"

echo "Allow data ingestion to App Insights from public  networks not connected through a Private Link Scope"
az monitor app-insights component update  \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --app "appi-${TRE_ID}" \
  --ingestion-access enabled


# Get the object id of the currently logged-in identity
if [[ -n ${ARM_CLIENT_ID:-} ]]; then
  # if environment includes a SP with subscription access, then we should use that.
  LOGGED_IN_OBJECT_ID=$(az ad sp show --id "${ARM_CLIENT_ID}" --query id -o tsv)
else
  LOGGED_IN_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv)
fi

# Assign Role Permissions.
az role assignment create \
    --role "Azure Service Bus Data Sender" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "${SERVICE_BUS_RESOURCE_ID}"

az role assignment create \
    --role "Azure Service Bus Data Receiver" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "${SERVICE_BUS_RESOURCE_ID}"

az role assignment create \
    --role "Contributor" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "${STATE_STORE_RESOURCE_ID}"

ROLE_DEFINITION_ID=$(az cosmosdb sql role definition list \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --account-name "${COSMOSDB_ACCOUNT_NAME}" \
    --query "[?roleName=='Cosmos DB Built-in Data Contributor'].id" \
    --output tsv)

az cosmosdb sql role assignment create \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --account-name "${COSMOSDB_ACCOUNT_NAME}" \
    --role-definition-id "${ROLE_DEFINITION_ID}" \
    --principal-id "${LOGGED_IN_OBJECT_ID}" \
    --scope "${STATE_STORE_RESOURCE_ID}"

az role assignment create \
    --role "Contributor" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "${COSMOSDB_MONGO_RESOURCE_ID}"

az role assignment create \
    --role "EventGrid Data Sender" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "${EVENT_GRID_STATUS_CHANGED_TOPIC_RESOURCE_ID}"

az role assignment create \
    --role "EventGrid Data Sender" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "${EVENT_GRID_AIRLOCK_NOTIFICATION_TOPIC_RESOURCE_ID}"

# For end to E2E add Storage Blob Data Contributor role to the logged in user
az role assignment create \
    --role "Storage Blob Data Contributor" \
    --assignee "${LOGGED_IN_OBJECT_ID}" \
    --scope "/subscriptions/${AZURE_SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_NAME}/providers/Microsoft.Storage/storageAccounts/stalimex${TRE_ID}"


if [[ -z ${ARM_CLIENT_ID:-} ]]; then
  # Configure SP for local resource processor debugging (Porter can't use local creds)
  echo "Configuring Service Principal for Resource Processor debugging..."
  RP_TESTING_SP=$(az ad sp create-for-rbac --name "ResourceProcessorTesting-${TRE_ID}" --role Owner --scopes /subscriptions/"${AZURE_SUBSCRIPTION_ID}" -o json)
  RP_TESTING_SP_APP_ID=$(echo "${RP_TESTING_SP}" | jq -r .appId)
  RP_TESTING_SP_PASSWORD=$(echo "${RP_TESTING_SP}" | jq -r .password)
else
  # no need to create a new sp if we already have one available
  RP_TESTING_SP_APP_ID=${ARM_CLIENT_ID}
  RP_TESTING_SP_PASSWORD=${ARM_CLIENT_SECRET}
fi

# Assign Service Bus permissions to the Resource Processor SP
az role assignment create \
    --role "Azure Service Bus Data Sender" \
    --assignee "${RP_TESTING_SP_APP_ID}" \
    --scope "${SERVICE_BUS_RESOURCE_ID}"

az role assignment create \
    --role "Azure Service Bus Data Receiver" \
    --assignee "${RP_TESTING_SP_APP_ID}" \
    --scope "${SERVICE_BUS_RESOURCE_ID}"

# Assign get permissions on the keyvault
az role assignment create \
    --role "Key Vault Secrets User" \
    --assignee "${RP_TESTING_SP_APP_ID}" \
    --scope "${KEYVAULT_RESOURCE_ID}"

# Write the appId and secret to the private.env file which is used for RP debugging
# First check if the env vars are there already and delete them
sed -i '/ARM_CLIENT_ID/d' "${private_env_path}"
sed -i '/ARM_CLIENT_SECRET/d' "${private_env_path}"
sed -i '/AAD_TENANT_ID/d' "${private_env_path}"
sed -i '/APPLICATION_ADMIN_CLIENT_ID/d' "${private_env_path}"
sed -i '/APPLICATION_ADMIN_CLIENT_SECRET/d' "${private_env_path}"
sed -i '/TEST_WORKSPACE_APP_ID/d' "${private_env_path}"
sed -i '/TEST_WORKSPACE_APP_SECRET/d' "${private_env_path}"

# Append them to the TRE file so that the Resource Processor can use them
tee -a "${private_env_path}" <<EOF
ARM_CLIENT_ID=${RP_TESTING_SP_APP_ID}
ARM_CLIENT_SECRET=${RP_TESTING_SP_PASSWORD}
AAD_TENANT_ID=${AAD_TENANT_ID}
APPLICATION_ADMIN_CLIENT_ID=${APPLICATION_ADMIN_CLIENT_ID}
APPLICATION_ADMIN_CLIENT_SECRET=${APPLICATION_ADMIN_CLIENT_SECRET}
TEST_WORKSPACE_APP_ID=${WORKSPACE_API_CLIENT_ID}
TEST_WORKSPACE_APP_SECRET=${WORKSPACE_API_CLIENT_SECRET}
EOF

# copy porter configuration to porter home
cp  ./resource_processor/vmss_porter/config.yaml ~/.porter/config.yaml

echo "Local debugging configuration complete. The vscode debug profiles for the API and Resource Processor are ready to use."
