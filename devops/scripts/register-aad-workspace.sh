#!/bin/bash
set -e

: ${AAD_TENANT_ID?"You have not set you AAD_TENANT_ID in ./templates/core/.env"}

LOGGED_IN_TENANT_ID=$(az account show --query tenantId -o tsv)

if [ "${LOGGED_IN_TENANT_ID}" != "${AAD_TENANT_ID}" ]; then
  echo "Attempting to sign you onto ${AAD_TENANT_ID} to add an App Registration"

  # First we need to login to the AAD tenant (as it could be different to the subscription tenant)
  az login --tenant ${AAD_TENANT_ID} --allow-no-subscriptions
fi

# Then register an App
./scripts/aad-app-reg.sh \
-n "${TRE_ID} - Workspace One" \
-r "https://${TRE_ID}.${RESOURCE_LOCATION}.cloudapp.azure.com/api/docs/oauth2-redirect" \
-w
