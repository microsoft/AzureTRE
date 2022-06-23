#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

: "${AAD_TENANT_ID?'You have not set your AAD_TENANT_ID in ./templates/core/.env'}"

LOGGED_IN_TENANT_ID=$(az account show --query tenantId -o tsv)
CHANGED_TENANT=0

if [ "${LOGGED_IN_TENANT_ID}" != "${AAD_TENANT_ID}" ]; then
  echo "Attempting to sign you onto ${AAD_TENANT_ID} to add an App Registration."

  # First we need to login to the AAD tenant (as it is different to the subscription tenant)
  az login --tenant "${AAD_TENANT_ID}" --allow-no-subscriptions --use-device-code
  CHANGED_TENANT=1
fi

APPLICATION_PERMISSION="Application.ReadWrite.OwnedBy"
if [ "${AUTO_WORKSPACE_APP_REGISTRATION}" == true ]; then
  APPLICATION_PERMISSION="Application.ReadWrite.All"
fi

# Create the identity that is able to administer other applications
./devops/scripts/aad/create_application_administrator.sh \
--name "${TRE_ID}" --admin-consent --application-permission "${APPLICATION_PERMISSION}"

echo "Please copy the values above into your /templates/core/.env."
read -p "Please confirm you have done this? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  exit 0
fi

# Then register an App for the TRE Core.
./devops/scripts/aad/aad-app-reg.sh \
  --name "${TRE_ID}" \
  --tre-url "https://${TRE_ID}.${LOCATION}.cloudapp.azure.com" \
  --admin-consent --automation-account

echo "Please copy the values above into your /templates/core/.env."
read -p "Please confirm you have done this? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 0
fi

# Load the new values back in
set -a
# shellcheck disable=SC1091
. ./templates/core/.env

echo "Please check that the following value is the same as above to check you have copied your keys."
echo "API client id is : ${API_CLIENT_ID}"

./devops/scripts/aad/aad-app-reg.sh \
  --name "${TRE_ID} - workspace 1" \
  --workspace --admin-consent \
  --swaggerui-clientid "${SWAGGER_UI_CLIENT_ID}" \
  --automation-clientid "${TEST_ACCOUNT_CLIENT_ID}"

if [ "${CHANGED_TENANT}" -ne 0 ]; then
  echo "Attempting to sign you back into ${LOGGED_IN_TENANT_ID}."

  # Log back into the tenant the user started on.
  az login --tenant "${LOGGED_IN_TENANT_ID}" --allow-no-subscriptions
fi
