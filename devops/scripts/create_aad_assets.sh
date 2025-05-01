#!/bin/bash
set -euo pipefail
# Use this for debug only
# set -o xtrace

: "${AAD_TENANT_ID?'You have not set your aad_tenant_id in ./config.yaml'}"

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

CHANGED_TENANT=0
LOGGED_IN_TENANT_ID=$(az account show --query tenantId -o tsv)

if [ "${LOGGED_IN_TENANT_ID}" != "${AAD_TENANT_ID}" ]; then
  echo "Attempting to sign you onto ${AAD_TENANT_ID} to setup Azure Active Directory assets."

  # First we need to login to the AAD tenant (as it is different to the subscription tenant)
  az login --tenant "${AAD_TENANT_ID}" --allow-no-subscriptions --use-device-code
  CHANGED_TENANT=1
fi

RESET_PASSWORDS=1
if [ "${RESET_AAD_PASSWORDS:-}" == false ]; then
  RESET_PASSWORDS=0
fi

# Initialize an array for permissions
APPLICATION_PERMISSIONS=()
APPLICATION_PERMISSIONS+=("Application.ReadWrite.OwnedBy")

if [ "${AUTO_WORKSPACE_APP_REGISTRATION:-}" == true ]; then
  APPLICATION_PERMISSIONS+=("Application.ReadWrite.All" "Directory.Read.All")
fi

if [ "${AUTO_WORKSPACE_GROUP_CREATION:-}" == true ]; then
  APPLICATION_PERMISSIONS+=("Group.ReadWrite.All")
fi

if [ "${AUTO_GRANT_WORKSPACE_CONSENT:-}" == true ]; then
  APPLICATION_PERMISSIONS+=("Application.ReadWrite.All" "DelegatedPermissionGrant.ReadWrite.All")
fi

# Check if the array contains more than 1 item
if [ ${#APPLICATION_PERMISSIONS[@]} -gt 1 ]; then
  # Check for and remove duplicates
  mapfile -t APPLICATION_PERMISSIONS < <(printf "%s\n" "${APPLICATION_PERMISSIONS[@]}" | sort -u)
fi

# Join the array into a comma-separated string
APPLICATION_PERMISSION=$(IFS=,; echo "${APPLICATION_PERMISSIONS[*]}")

# Create the identity that is able to administer other applications
"$DIR/aad/create_application_administrator.sh" \
  --name "${TRE_ID}" \
  --admin-consent \
  --application-permission "${APPLICATION_PERMISSION}" \
  --reset-password $RESET_PASSWORDS

# Create the identity that is able to automate the testing
"$DIR/aad/create_automation_administrator.sh" \
  --name "${TRE_ID}" \
  --reset-password $RESET_PASSWORDS

# Load the new values back in because
# we need TEST_ACCOUNT_CLIENT_ID
# shellcheck disable=SC1091
. "$DIR/load_and_validate_env.sh"

# Then register an App for the TRE Core.
"$DIR/aad/create_api_application.sh" \
  --name "${TRE_ID}" \
  --tre-url "${TRE_URL}" \
  --admin-consent --automation-clientid "${TEST_ACCOUNT_CLIENT_ID}" \
  --reset-password $RESET_PASSWORDS \
  --custom-domain "${CUSTOM_DOMAIN}"

if [ "${AUTO_WORKSPACE_APP_REGISTRATION:=false}" == false ]; then
  # Load the new values back in
  # This is because we want the SWAGGER_UI_CLIENT_ID
  # shellcheck disable=SC1091
  . "$DIR/load_and_validate_env.sh"

  "$DIR/aad/create_workspace_application.sh" \
    --name "${TRE_ID} - workspace 1" \
    --admin-consent \
    --ux-clientid "${SWAGGER_UI_CLIENT_ID}" \
    --automation-clientid "${TEST_ACCOUNT_CLIENT_ID}" \
    --application-admin-clientid "${APPLICATION_ADMIN_CLIENT_ID}" \
    --reset-password $RESET_PASSWORDS
fi

if [ "${CHANGED_TENANT}" -ne 0 ]; then
  echo "Attempting to sign you back into ${LOGGED_IN_TENANT_ID}."

  # Log back into the tenant the user started on.
  az login --tenant "${LOGGED_IN_TENANT_ID}" --allow-no-subscriptions
fi
