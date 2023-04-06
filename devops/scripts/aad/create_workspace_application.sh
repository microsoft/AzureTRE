#!/bin/bash
set -euo pipefail
# Use this for debug only
# set -o xtrace
# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for creating a workspace TRE. You would typically have one of these per workspace
for a security boundary.
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 [--admin-consent]

Options:
    -n,--name                       Required. The prefix for the app (registration) names e.g., "TRE".
    -u,--ux-clientid                Required. The client ID of the UX must be provided.
    -y,--application-admin-clientid Required. The client ID of the Application Administrator that will be able to update this application.
                                    e.g. updating a redirect URI.
    -a,--admin-consent              Optional, but recommended. Grants admin consent for the app registrations, when this flag is set.
                                    Requires directory admin privileges to the Azure AD in question.
    -z,--automation-clientid        Optional, the client ID of the automation account can be added to the TRE workspace.
    -r,--reset-password             Optional, switch to automatically reset the password. Default 0

USAGE
    exit 2
}

if ! command -v az &> /dev/null; then
    echo "This script requires Azure CLI" 1>&2
    exit 1
fi

if [[ $(az account list --only-show-errors -o json | jq 'length') -eq 0 ]]; then
    echo "Please run az login -t <tenant> --allow-no-subscriptions"
    exit 1
fi

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

declare resetPassword=0
declare spPassword=""
declare grantAdminConsent=0
declare currentUserId=""
declare uxClientId=""
declare msGraphUri=""
declare appName=""
declare automationClientId=""
declare applicationAdminClientId=""
declare applicationAdminObjectId=""

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
        -y|--application-admin-clientid)
            applicationAdminClientId=$2
            shift 2
        ;;
        -u|--ux-clientid)
            uxClientId=$2
            shift 2
        ;;
        -z|--automation-clientid)
            automationClientId=$2
            shift 2
        ;;
        -r|--reset-password)
            resetPassword=$2
            shift 2
        ;;
        *)
            echo "Invalid option: $1."
            show_usage
        ;;
    esac
done

###################################
# CHECK INCOMMING PARAMETERS      #
###################################
if [[ -z "$appName" ]]; then
    echo "Please specify the application name." 1>&2
    show_usage
fi
appName="$appName API"
if [[ -z "$applicationAdminClientId" ]]; then
    echo "Please specify the client id of the Application Admin." 1>&2
    show_usage
fi
applicationAdminObjectId=$(az ad sp show --id "${applicationAdminClientId}" --query id -o tsv --only-show-errors)
currentUserId=$(az ad signed-in-user show --query 'id' --output tsv --only-show-errors)
msGraphUri="$(az cloud show --query endpoints.microsoftGraphResourceId --output tsv)/v1.0"
tenant=$(az rest -m get -u "${msGraphUri}/domains" -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo -e "\e[96mCreating a Workspace Application in the \"${tenant}\" Azure AD tenant.\e[0m"

# Load in helper functions
# shellcheck disable=SC1091
source "${DIR}/get_existing_app.sh"
# shellcheck disable=SC1091
source "${DIR}/grant_admin_consent.sh"
# shellcheck disable=SC1091
source "${DIR}/wait_for_new_app_registration.sh"
# shellcheck disable=SC1091
source "${DIR}/create_or_update_service_principal.sh"
# shellcheck disable=SC1091
source "${DIR}/get_msgraph_access.sh"
# shellcheck disable=SC1091
source "${DIR}/update_resource_access.sh"

# Default of new UUIDs
researcherRoleId=$(cat /proc/sys/kernel/random/uuid)
ownerRoleId=$(cat /proc/sys/kernel/random/uuid)
airlockManagerRoleId=$(cat /proc/sys/kernel/random/uuid)
userImpersonationScopeId=$(cat /proc/sys/kernel/random/uuid)
appObjectId=""

# Get an existing object if its been created before.
existingApp=$(get_existing_app --name "${appName}") || null
if [ -n "${existingApp}" ]; then
    appObjectId=$(echo "${existingApp}" | jq -r '.id')

    researcherRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "WorkspaceResearcher").id')
    ownerRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "WorkspaceOwner").id')
    airlockManagerRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "AirlockManager").id')
    userImpersonationScopeId=$(echo "$existingApp" | jq -r '.api.oauth2PermissionScopes[] | select(.value == "user_impersonation").id')
    if [[ -z "${researcherRoleId}" ]]; then researcherRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${ownerRoleId}" ]]; then ownerRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${airlockManagerRoleId}" ]]; then airlockManagerRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${userImpersonationScopeId}" ]]; then userImpersonationScopeId=$(cat /proc/sys/kernel/random/uuid); fi
fi

# Get the Required Resource Scope/Role
msGraphAppId="00000003-0000-0000-c000-000000000000"
msGraphObjectId=$(az ad sp show --id ${msGraphAppId} --query "id" --output tsv --only-show-errors)
msGraphEmailScopeId="64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0"
msGraphOpenIdScopeId="37f7f235-527c-4136-accd-4a02d197296e"
msGraphProfileScopeId="14dad69e-099b-42c9-810b-d002981feec1"

appDefinition=$(jq -c . << JSON
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
          }
        ]
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
    },
    {
        "id": "${airlockManagerRoleId}",
        "allowedMemberTypes": [ "User", "Application" ],
        "description": "Provides airlock managers access to the Workspace and ability to review airlock requests",
        "displayName": "Airlock Manager",
        "isEnabled": true,
        "origin": "Application",
        "value": "AirlockManager"
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

# Is the Workspace app already registered?
if [[ -n ${appObjectId} ]]; then
  echo "Updating \"${appName}\" with ObjectId \"${appObjectId}\"."
  az rest --method PATCH --uri "${msGraphUri}/applications/${appObjectId}" --headers Content-Type=application/json --body "${appDefinition}"
  workspaceAppId=$(az ad app show --id "${appObjectId}" --query "appId" --output tsv --only-show-errors)
  echo "Workspace app registration with AppId \"${workspaceAppId}\" updated."
else
  echo "Creating \"${appName}\" app registration."
  workspaceAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${appDefinition}" --output tsv --query "appId")

  # Poll until the app registration is found in the listing.
  wait_for_new_app_registration "${workspaceAppId}"

  # Update to set the identifier URI.
  az ad app update --id "${workspaceAppId}" --identifier-uris "api://${workspaceAppId}" --only-show-errors
fi

# Make the current user an owner of the application.
az ad app owner add --id "${workspaceAppId}" --owner-object-id "$currentUserId" --only-show-errors
az ad app owner add --id "${workspaceAppId}" --owner-object-id "$applicationAdminObjectId" --only-show-errors

# Create a Service Principal for the app.
spPassword=$(create_or_update_service_principal "${workspaceAppId}" "${resetPassword}")
workspaceSpId=$(az ad sp list --filter "appId eq '${workspaceAppId}'" --query '[0].id' --output tsv --only-show-errors)

# needed to make the API permissions change effective, this must be done after SP creation...
echo
echo "Running 'az ad app permission grant' to make changes effective."
az ad app permission grant --id "$workspaceSpId" --api "$msGraphObjectId" --scope "email openid profile"  --only-show-errors

# The UX (which was created as part of the API) needs to also have access to this Workspace
echo "Searching for existing UX application (${uxClientId})."
existingUXApp=$(get_existing_app --id "${uxClientId}")
uxObjectId=$(echo "${existingUXApp}" | jq -r .id)

# This is the new API Access we require.
uxWorkspaceAccess=$(jq -c .requiredResourceAccess << JSON
{
  "requiredResourceAccess": [
    {
      "resourceAccess": [
          {
              "id": "${userImpersonationScopeId}",
              "type": "Scope"
          }
      ],
      "resourceAppId": "${workspaceAppId}"
    }
  ]
}
JSON
)

# Utility function to add the required permissions.
update_resource_access "$msGraphUri" "${uxObjectId}" "${workspaceAppId}" "${uxWorkspaceAccess}"

echo "Grant UX delegated access '${appName}' (Client ID ${uxClientId})"
az ad app permission grant --id "${uxClientId}" --api "${workspaceAppId}" --scope "user_impersonation" --only-show-errors

if [[ -n ${automationClientId} ]]; then
  echo "Searching for existing Automation application (${automationClientId})."
  existingAutomationApp=$(get_existing_app --id "${automationClientId}")

  automationAppObjectId=$(echo "${existingAutomationApp}" | jq -r .id)
  automationAppName=$(echo "${existingAutomationApp}" | jq -r .displayName)
  echo "Found '${automationAppName}' with ObjectId: '${automationAppObjectId}'"

  # This is the new API Access we require.
  automationWorkspaceAccess=$(jq -c .requiredResourceAccess << JSON
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
            },
            {
                "id": "${researcherRoleId}",
                "type": "Role"
            },
            {
                "id": "${airlockManagerRoleId}",
                "type": "Role"
            }
        ],
        "resourceAppId": "${workspaceAppId}"
    }
  ]
}
JSON
)

  # Utility function to add the required permissions.
  update_resource_access "$msGraphUri" "${automationAppObjectId}" "${workspaceAppId}" "${automationWorkspaceAccess}"

  # Grant admin consent for the delegated workspace scopes
  if [[ $grantAdminConsent -eq 1 ]]; then
      echo "Granting admin consent for \"${automationAppName}\" (Client ID ${automationClientId})"
      automationSpId=$(az ad sp list --filter "appId eq '${automationClientId}'" --query '[0].id' --output tsv --only-show-errors)
      echo "Found Service Principal \"$automationSpId\" for \"${automationAppName}\"."

      grant_admin_consent "${automationSpId}" "${workspaceSpId}" "${ownerRoleId}"
      grant_admin_consent "${automationSpId}" "${workspaceSpId}" "${airlockManagerRoleId}"
      grant_admin_consent "${automationSpId}" "${workspaceSpId}" "${researcherRoleId}"
      az ad app permission grant --id "$automationSpId" --api "$workspaceAppId" --scope "user_impersonation" --only-show-errors
  fi
fi

# Set outputs in configuration file
yq -i ".authentication.workspace_api_client_id |= \"${workspaceAppId}\"" config.yaml
yq -i ".authentication.workspace_api_client_secret |= \"${spPassword}\"" config.yaml

echo "workspace_api_client_id=\"${workspaceAppId}\""
echo "workspace_api_client_secret=\"${spPassword}\""

if [[ $grantAdminConsent -eq 0 ]]; then
    echo "NOTE: Make sure the API permissions of the app registrations have admin consent granted."
    echo "Run this script with flag -a to grant admin consent or configure the registrations in Azure Portal."
    echo "See APP REGISTRATIONS in documentation for more information."
fi
