#!/bin/bash

# Setup Script
set -euo pipefail
# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for creating a workspace TRE. You would typically have one of these per workspace
for a security boundary.
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 [--admin-consent]

Options:
    -n,--name                   Required. The prefix for the app (registration) names e.g., "TRE".
    -s,--swaggerui-clientid     Required. The client ID of the UX must be provided.
    -a,--admin-consent          Optional, but recommended. Grants admin consent for the app registrations, when this flag is set.
                                Requires directory admin privileges to the Azure AD in question.
    -z,--automation-clientid    Optional, the client ID of the automation account can be added to the TRE workspace.

USAGE
    exit 1
}

if ! command -v az &> /dev/null; then
    echo "This script requires Azure CLI" 1>&2
    exit 1
fi

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

declare grantAdminConsent=0
declare currentUserId=""
declare swaggerClientId=""
declare spId=""
declare msGraphUri="https://graph.microsoft.com/v1.0"
declare appName=""
declare automationClientId=""

# Initialize parameters specified from command line
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)
            appName=$2
            shift 2
        ;;
        -a|--admin-consent)
            grantAdminConsent=1
            shift 1
        ;;
        -s|--swaggerui-clientid)
            swaggerClientId=$2
            shift 2
        ;;
        --automation-clientid)
            automationClientId=$2
            shift 2
        ;;
        *)
            echo "Invalid option: $1."
            show_usage
            exit 2
        ;;
    esac
done

###################################
# CHECK INCOMMING PARAMETERS      #
###################################
if [[ $(az account list --only-show-errors -o json | jq 'length') -eq 0 ]]; then
    echo "Please run az login -t <tenant> --allow-no-subscriptions"
    exit 1
fi

if [[ -z "$appName" ]]; then
    echo "Please specify the application name" 1>&2
    show_usage
fi
appName="$appName API"
currentUserId=$(az ad signed-in-user show --query 'objectId' --output tsv --only-show-errors)
tenant=$(az rest -m get -u "${msGraphUri}/domains" -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo "You are about to create app registrations in the Azure AD tenant \"${tenant}\"."

# Load in helper functions
# shellcheck disable=SC1091
source "${DIR}/get_existing_app.sh"
# shellcheck disable=SC1091
source "${DIR}/grant_admin_consent.sh"
# shellcheck disable=SC1091
source "${DIR}/wait_for_new_app_registration.sh"
# shellcheck disable=SC1091
source "${DIR}/wait_for_new_service_principal.sh"
# shellcheck disable=SC1091
source "${DIR}/get_msgraph_access.sh"

# Default of new UUIDs
researcherRoleId=$(cat /proc/sys/kernel/random/uuid)
ownerRoleId=$(cat /proc/sys/kernel/random/uuid)
userImpersonationScopeId=$(cat /proc/sys/kernel/random/uuid)
appObjectId=""

# Get an existing object if it's been created before.
existingApp=$(get_existing_app --name "${appName}") || null
if [ -n "${existingApp}" ]; then
    appObjectId=$(echo "${existingApp}" | jq -r '.objectId')

    researcherRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "WorkspaceResearcher").id')
    ownerRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "WorkspaceOwner").id')
    if [[ -z "${researcherRoleId}" ]]; then researcherRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${ownerRoleId}" ]]; then ownerRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    userImpersonationScopeId=$(echo "$existingApp" | jq -r '.oauth2Permissions[] | select(.value == "user_impersonation").id')

    if [[ -z "${userImpersonationScopeId}" ]]; then userImpersonationScopeId=$(cat /proc/sys/kernel/random/uuid); fi
fi

# Get the Required Resource Scope/Role
msGraphAppId="00000003-0000-0000-c000-000000000000"
msGraphEmailScopeId="64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0"
msGraphOpenIdScopeId="37f7f235-527c-4136-accd-4a02d197296e"
msGraphProfileScopeId="14dad69e-099b-42c9-810b-d002981feec1"

apiApp=$(jq -c . << JSON
{
    "displayName": "${appName}",
    "api": {
        "requestedAccessTokenVersion": 2,
        "oauth2PermissionScopes": [
        {
            "adminConsentDescription": "Allow the app to access the Workspace API on behalf of the signed-in user.",
            "adminConsentDisplayName": "Access the Workspace API on behalf of signed-in user",
            "id": "${userImpersonationScopeId}",
            "isEnabled": true,
            "type": "User",
            "userConsentDescription": "Allow the app to access the Workspace API on your behalf.",
            "userConsentDisplayName": "Access the Workspace API",
            "value": "user_impersonation"
        }]
    },
    "appRoles": [
    {
        "id": "${ownerRoleId}",
        "allowedMemberTypes": [ "User", "Application" ],
        "description": "Provides workspace owners access to the Workspace.",
        "displayName": "Workspace Owner",
        "isEnabled": true,
        "origin": "Application",
        "value": "WorkspaceOwner"
    },
    {
        "id": "${researcherRoleId}",
        "allowedMemberTypes": [ "User", "Application" ],
        "description": "Provides researchers access to the Workspace.",
        "displayName": "Workspace Researcher",
        "isEnabled": true,
        "origin": "Application",
        "value": "WorkspaceResearcher"
    }],
    "signInAudience": "AzureADMyOrg",
    "requiredResourceAccess": [
        {
            "resourceAppId": "${msGraphAppId}",
            "resourceAccess": [
                {
                    "id": "${msGraphEmailScopeId}",
                    "type": "Scope"
                },
                {
                    "id": "${msGraphOpenIdScopeId}",
                    "type": "Scope"
                },
                {
                    "id": "${msGraphProfileScopeId}",
                    "type": "Scope"
                }
            ]
        }
    ],
    "web":{
        "implicitGrantSettings":{
            "enableIdTokenIssuance":true,
            "enableAccessTokenIssuance":true
        }
    },
    "optionalClaims": {
        "idToken": [
            {
                "name": "ipaddr",
                "source": null,
                "essential": false,
                "additionalProperties": []
            },
            {
                "name": "email",
                "source": null,
                "essential": false,
                "additionalProperties": []
            }
        ],
        "accessToken": [],
        "saml2Token": []
    }
}
JSON
)

# Is the API app already registered?
if [[ -n ${appObjectId} ]]; then
    echo "Updating API app registration with ID ${appObjectId}"
    az rest --method PATCH --uri "${msGraphUri}/applications/${appObjectId}" --headers Content-Type=application/json --body "${apiApp}"
    apiAppId=$(az ad app show --id "${appObjectId}" --query "appId" --output tsv --only-show-errors)
    echo "API app registration with ID ${apiAppId} updated"
else
    echo "Creating a new API app registration, ${appName}"
    apiAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${apiApp}" --output tsv --query "appId")
    echo "AppId: ${apiAppId}"

    # Poll until the app registration is found in the listing.
    wait_for_new_app_registration "${apiAppId}"

    # Update to set the identifier URI.
    echo "Updating identifier URI 'api://${apiAppId}'"
    az ad app update --id "${apiAppId}" --identifier-uris "api://${apiAppId}" --only-show-errors
fi

# Make the current user an owner of the application.
az ad app owner add --id "${apiAppId}" --owner-object-id "$currentUserId" --only-show-errors

# See if a service principal already exists
spId=$(az ad sp list --filter "appId eq '${apiAppId}'" --query '[0].objectId' --output tsv --only-show-errors)

resetPassword=0

# If not, create a new service principal
if [[ -z "$spId" ]]; then
    spId=$(az ad sp create --id "${apiAppId}" --query 'objectId' --output tsv --only-show-errors)
    echo "Creating a new service principal, for '${appName}' app, with ID ${spId}"
    wait_for_new_service_principal "${spId}"
    az ad app owner add --id "${apiAppId}" --owner-object-id "${spId}" --only-show-errors
    resetPassword=1
else
    echo "Service principal for the app already exists."
    echo "Existing passwords (client secrets) cannot be queried. To view the password it needs to be reset."
    read -p "Do you wish to reset the ${appName} app password (y/N)? " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        resetPassword=1
    fi
fi

spPassword=""

if [[ "$resetPassword" == 1 ]]; then
    # Reset the app password (client secret) and display it
    spPassword=$(az ad sp credential reset --name "${apiAppId}" --query 'password' --output tsv --only-show-errors)
    echo "'${appName}' app password (client secret): ${spPassword}"
fi

# This tag ensures the app is listed in "Enterprise applications"
az ad sp update --id "$spId" --set tags="['WindowsAzureActiveDirectoryIntegratedApp']" --only-show-errors

# needed to make the API permissions change effective, this must be done after SP creation...
echo "running 'az ad app permission grant' to make changes effective"
az ad app permission grant --id "${apiAppId}" --api "${msGraphAppId}" --only-show-errors

# The Swagger UI (which was created as part of the API) needs to also have access to this Workspace
echo "Searching for existing Swagger application (${swaggerClientId})."
existingSwaggerApp=$(get_existing_app --id "${swaggerClientId}")
swaggerObjectId=$(echo "${existingSwaggerApp}" | jq -r .objectId)

# Get the existing required resource access from the swagger app,
# but remove the access that we are about to add for idempotency. We cant use
# the response from az cli as it returns an 'AdditionalProperties' element in
# the json
existingResourceAccess=$(az rest \
  --method GET \
  --uri "${msGraphUri}/applications/${swaggerObjectId}" \
  --headers Content-Type=application/json -o json \
  | jq -r --arg apiAppId "${apiAppId}" \
  'del(.requiredResourceAccess[] | select(.resourceAppId==$apiAppId)) | .requiredResourceAccess' \
  )

# Add the existing resource access so we don't remove any existing permissions.
swaggerWorkspaceAccess=$(jq -c . << JSON
{
  "requiredResourceAccess": [
  {
    "resourceAccess": [
        {
            "id": "${userImpersonationScopeId}",
            "type": "Scope"
        }
    ],
    "resourceAppId": "${apiAppId}"
  }],
  "existingAccess": ${existingResourceAccess}
}
JSON
)

# Manipulate the json (add existingAccess into requiredResourceAccess and then remove it)
requiredResourceAccess=$(echo "${swaggerWorkspaceAccess}" | \
  jq '.requiredResourceAccess += .existingAccess | {requiredResourceAccess}')

az rest --method PATCH \
  --uri "${msGraphUri}/applications/${swaggerObjectId}" \
  --headers Content-Type=application/json \
  --body "${requiredResourceAccess}"

echo "Grant Swagger UI delegated access '${appName}' (Client ID ${swaggerClientId})"
az ad app permission grant --id "${swaggerClientId}" --api "${apiAppId}" --scope "user_impersonation" --only-show-errors

if [[ -n ${automationClientId} ]]; then
  echo "Searching for existing Automation application (${automationClientId})."
  existingAutomationApp=$(get_existing_app --id "${automationClientId}")

  automationAppObjectId=$(echo "${existingAutomationApp}" | jq -r .objectId)
  automationAppName=$(echo "${existingAutomationApp}" | jq -r .displayName)
  echo "Found '${automationAppName}' with ObjectId: '${automationAppObjectId}'"

  # Get the existing required resource access from the automation app,
  # but remove the access that we are about to add for idempotency. We cant use
  # the response from az cli as it returns an 'AdditionalProperties' element in
  # the json
  existingResourceAccess=$(az rest \
    --method GET \
    --uri "${msGraphUri}/applications/${automationAppObjectId}" \
    --headers Content-Type=application/json -o json \
    | jq -r --arg apiAppId "${apiAppId}" \
    'del(.requiredResourceAccess[] | select(.resourceAppId==$apiAppId)) | .requiredResourceAccess' \
    )

  # Add the existing resource access so we don't remove any existing permissions.
  automationWorkspaceAccess=$(jq -c . << JSON
{
  "requiredResourceAccess": [
    {
        "resourceAccess": [
            {
                "id": "${userImpersonationScopeId}",
                "type": "Scope"
            },
            {
                "id": "${ownerRoleId}",
                "type": "Role"
            }
        ],
        "resourceAppId": "${apiAppId}"
    }
  ],
  "existingAccess": ${existingResourceAccess}
}
JSON
)

  # Manipulate the json (add existingAccess into requiredResourceAccess and then remove it)
  requiredResourceAccess=$(echo "${automationWorkspaceAccess}" | \
    jq '.requiredResourceAccess += .existingAccess | {requiredResourceAccess}')

  az rest --method PATCH \
    --uri "${msGraphUri}/applications/${automationAppObjectId}" \
    --headers Content-Type=application/json \
    --body "${requiredResourceAccess}"

  # We've just updated a required resource. Wait for the update to complete.
  wait_for_new_app_registration "${automationClientId}"

  # Grant admin consent for the delegated workspace scopes
  if [[ $grantAdminConsent -eq 1 ]]; then
      echo "Granting admin consent for ${automationAppName} (Client ID ${automationClientId})"
      az ad app permission admin-consent --id "${automationClientId}" --only-show-errors
      az ad app permission list --id "${automationClientId}" --only-show-errors
      az ad app permission admin-consent --id "${automationClientId}" --only-show-errors
  fi
fi

cat << ENV_VARS

AAD_TENANT_ID="$(az account show --output json | jq -r '.tenantId')"

** Please copy the following variables to /templates/core/.env **

WORKSPACE_API_CLIENT_ID="${apiAppId}"
WORKSPACE_API_CLIENT_SECRET="${spPassword}"

ENV_VARS

if [[ $grantAdminConsent -eq 0 ]]; then
    echo "NOTE: Make sure the API permissions of the app registrations have admin consent granted."
    echo "Run this script with flag -a to grant admin consent or configure the registrations in Azure Portal."
    echo "See APP REGISTRATIONS in documentation for more information."
fi
