#!/bin/bash
set -euo pipefail
# Use this for debug only
# set -o xtrace

# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for creating app registrations required by Azure TRE. This script will create the API and Client
Applications. The Client Application is the public facing app, whereas the API is an internal AAD Application.
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 -n <app-name> [-r <reply-url>] [-a] [-s] [--automation-account]

Options:
    -n,--name                   Required. The prefix for the app (registration) names e.g., "TRE", or "Workspace One".
    -u,--tre-url                TRE URL, used to construct auth redirection URLs for the UI and Swagger app.
    -a,--admin-consent          Optional, but recommended. Grants admin consent for the app registrations, when this flag is set.
                                Requires directory admin privileges to the Azure AD in question.
    -t,--automation-clientid    Optional, when --workspace is specified the client ID of the automation account can be added to the TRE workspace.
    -r,--reset-password         Optional, switch to automatically reset the password. Default 0
    -d,--custom-domain          Optional, custom domain, used to construct auth redirection URLs (in addition to --tre-url)

Examples:
    1. $0 -n TRE -r https://mytre.region.cloudapp.azure.com -a

    Using an Automation account
    3. $0 --name 'TRE' --tre-url https://mytre.region.cloudapp.azure.com --admin-consent --automation-account

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
declare grantAdminConsent=0
declare appName=""
declare appId=""
declare uxAppName=""
declare uxAppId=""
declare treUrl=""
declare currentUserId=""
declare automationAppId=""
declare automationAppObjectId=""
declare msGraphUri=""
declare spPassword=""
declare customDomain=""

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
        -u|--tre-url)
            treUrl=$2
            shift 2
        ;;
        -t|--automation-clientid)
            automationAppId=$2
            shift 2
        ;;
        -r|--reset-password)
            resetPassword=$2
            shift 2
        ;;
        -d|--custom-domain)
            customDomain=$2
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
    echo "Please specify the application name" 1>&2
    show_usage
fi
uxAppName="$appName UX"
appName="$appName API"
currentUserId=$(az ad signed-in-user show --query 'id' --output tsv --only-show-errors)
msGraphUri="$(az cloud show --query endpoints.microsoftGraphResourceId --output tsv)/v1.0"
tenant=$(az rest -m get -u "${msGraphUri}/domains" -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo -e "\e[96mCreating the API/UX Application in the \"${tenant}\" Azure AD tenant.\e[0m"

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

# Generate GUIDS
userRoleId=$(cat /proc/sys/kernel/random/uuid)
adminRoleId=$(cat /proc/sys/kernel/random/uuid)
userImpersonationScopeId=$(cat /proc/sys/kernel/random/uuid)
appObjectId=""

# Get an existing object if it's been created before.
existingApp=$(get_existing_app --name "${appName}")
if [[ -n ${existingApp} ]]; then
    appObjectId=$(echo "${existingApp}" | jq -r '.id')
    userRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "TREUser").id')
    adminRoleId=$(echo "$existingApp" | jq -r '.appRoles[] | select(.value == "TREAdmin").id')
    userImpersonationScopeId=$(echo "$existingApp" | jq -r '.api.oauth2PermissionScopes[] | select(.value == "user_impersonation").id')
    if [[ -z "${userRoleId}" ]]; then userRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${adminRoleId}" ]]; then adminRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${userImpersonationScopeId}" ]]; then userImpersonationScopeId=$(cat /proc/sys/kernel/random/uuid); fi
fi

msGraphAppId="00000003-0000-0000-c000-000000000000"
msGraphObjectId=$(az ad sp show --id ${msGraphAppId} --query "id" --output tsv --only-show-errors)

roleUserReadAll=$(get_msgraph_role "User.Read.All" )
roleDirectoryReadAll=$(get_msgraph_role "Directory.Read.All" )
scope_email=$(get_msgraph_scope "email")
scope_profile=$(get_msgraph_scope "profile")
scope_openid=$(get_msgraph_scope "openid")
scope_offline_access=$(get_msgraph_scope "offline_access")

appDefinition=$(jq -c . << JSON
{
  "displayName": "${appName}",
  "api": {
      "requestedAccessTokenVersion": 2,
      "oauth2PermissionScopes": [
        {
          "adminConsentDescription": "Allow the app to access the TRE API on behalf of the signed-in user.",
          "adminConsentDisplayName": "Access the TRE API on behalf of signed-in user",
          "id": "${userImpersonationScopeId}",
          "isEnabled": true,
          "type": "User",
          "userConsentDescription": "Allow the app to access the TRE API on your behalf.",
          "userConsentDisplayName": "Access the TRE API",
          "value": "user_impersonation"
        }
      ]
  },
  "appRoles": [
    {
        "id": "${userRoleId}",
        "allowedMemberTypes": [ "User", "Application" ],
        "description": "Provides access to the ${appName} application.",
        "displayName": "TRE Users",
        "isEnabled": true,
        "origin": "Application",
        "value": "TREUser"
    },
    {
        "id": "${adminRoleId}",
        "allowedMemberTypes": [ "User", "Application" ],
        "description": "Provides resource administrator access to the ${appName}.",
        "displayName": "TRE Administrators",
        "isEnabled": true,
        "origin": "Application",
        "value": "TREAdmin"
    }
  ],
  "signInAudience": "AzureADMyOrg",
  "requiredResourceAccess": [
    {
      "resourceAppId": "${msGraphAppId}",
      "resourceAccess": [
          ${roleUserReadAll},
          ${roleDirectoryReadAll},
          $scope_email,
          $scope_openid,
          $scope_profile
      ]
    }
  ]
}
JSON
)

# Is the app already registered?
if [[ -n ${appObjectId} ]]; then
  echo "Updating \"${appName}\" app registration (ObjectId: \"${appObjectId}\")"
  az rest --method PATCH --uri "${msGraphUri}/applications/${appObjectId}" --headers Content-Type=application/json --body "${appDefinition}"
  appId=$(az ad app show --id "${appObjectId}" --query "appId" --output tsv --only-show-errors)
  echo "Updated \"${appName}\" app registration (AppId: \"${appId}\")"
else
  echo "Creating \"${appName}\" app registration."
  appId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${appDefinition}" --output tsv --query "appId")

    # Poll until the app registration is found in the listing.
  wait_for_new_app_registration "${appId}"

  az ad app update --id "${appId}" --identifier-uris "api://${appId}" --only-show-errors
fi

# Make the current user an owner of the application.
az ad app owner add --id "${appId}" --owner-object-id "$currentUserId" --only-show-errors

# Create a Service Principal for the app.
spPassword=$(create_or_update_service_principal "${appId}" "${resetPassword}")
spId=$(az ad sp list --filter "appId eq '${appId}'" --query '[0].id' --output tsv --only-show-errors)

# needed to make the API permissions change effective, this must be done after SP creation...
echo
echo "Running 'az ad app permission grant' to make changes effective."
az ad app permission grant --id "$spId" --api "$msGraphObjectId" --scope "email openid profile"  --only-show-errors

# Grant admin consent on the required resource accesses (Graph API)
if [[ $grantAdminConsent -eq 1 ]]; then
  echo "Granting admin consent for '${appName}' app (service principal ID ${spId}) - NOTE: Directory admin privileges required for this step"
  directoryReadAllId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='Directory.Read.All'].id" --output tsv --only-show-errors)
  grant_admin_consent "${spId}" "$msGraphObjectId" "${directoryReadAllId}"
  userReadAllId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='User.Read.All'].id" --output tsv --only-show-errors)
  grant_admin_consent "${spId}" "${msGraphObjectId}" "${userReadAllId}"
fi

# Create the UX App Registration
redirectUris="\"http://localhost:8000/api/docs/oauth2-redirect\", \"http://localhost:3000\""
if [[ -n ${treUrl} ]]; then
    echo "Adding reply/redirect URL \"${treUrl}\" to \"${appName}\""
    redirectUris="${redirectUris}, \"${treUrl}\", \"${treUrl}/api/docs/oauth2-redirect\""
fi
if [[ -n ${customDomain} ]]; then
    customDomainUrl="https://${customDomain}"
    echo "Adding reply/redirect URL \"${customDomainUrl}\" to \"${appName}\""
    redirectUris="${redirectUris}, \"${customDomainUrl}\", \"${customDomainUrl}/api/docs/oauth2-redirect\""
fi

uxAppDefinition=$(jq -c . << JSON
{
  "displayName": "${uxAppName}",
  "signInAudience": "AzureADMyOrg",
  "requiredResourceAccess": [
    {
        "resourceAppId": "${msGraphAppId}",
        "resourceAccess": [
            ${scope_openid},
            ${scope_offline_access}
        ]
    },
    {
        "resourceAppId": "${appId}",
        "resourceAccess": [
            {
                "id": "${userImpersonationScopeId}",
                "type": "Scope"
            }
        ]
    }
  ],
  "spa": {
      "redirectUris": [
          ${redirectUris}
      ]
  }
}
JSON
)

# Is the UX app already registered?
existingUXApp=$(get_existing_app --name "${uxAppName}")
if [[ -n ${existingUXApp} ]]; then
  uxObjectId=$(echo "${existingUXApp}" | jq -r '.id')
  echo "Updating \"${uxAppName}\" with ObjectId \"${uxObjectId}\""
  az rest --method PATCH --uri "${msGraphUri}/applications/${uxObjectId}" --headers Content-Type=application/json --body "${uxAppDefinition}"
  uxAppId=$(az ad app show --id "${uxObjectId}" --query "appId" --output tsv --only-show-errors)
  echo "UX app registration with AppId \"${uxAppId}\" updated."
else
  echo "Creating \"${uxAppName}\" app registration."
  uxAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${uxAppDefinition}" --output tsv --query "appId")

  # Poll until the app registration is found in the listing.
  wait_for_new_app_registration "${uxAppId}"
fi

# See if a service principal already exists
uxSpId=$(az ad sp list --filter "appId eq '${uxAppId}'" --query '[0].id' --output tsv --only-show-errors)

# If not, create a new service principal
if [[ -z "$uxSpId" ]]; then
    uxSpId=$(az ad sp create --id "${uxAppId}" --query 'id' --output tsv --only-show-errors)
    wait_for_new_service_principal "${uxSpId}"
fi

# Make the current user an owner of the application.
az ad app owner add --id "${uxAppId}" --owner-object-id "${currentUserId}" --only-show-errors
az ad app owner add --id "${uxAppId}" --owner-object-id "${uxSpId}" --only-show-errors

echo "Granting delegated access for \"${uxAppName}\" (service principal ID ${uxSpId})"
az ad app permission grant --id "$uxSpId" --api "$msGraphObjectId" --scope "offline_access openid"  --only-show-errors
az ad app permission grant --id "$uxSpId" --api "$appId" --scope "user_impersonation" --only-show-errors

if [[ -n ${automationAppId} ]]; then
  existingAutomationApp=$(get_existing_app --id "${automationAppId}")

  automationAppObjectId=$(echo "${existingAutomationApp}" | jq -r .id)
  automationAppName=$(echo "${existingAutomationApp}" | jq -r .displayName)
  echo "Found '${automationAppName}' with ObjectId: '${automationAppObjectId}'"

  # This is the new API Access we require.
  automationApiAccess=$(jq -c .requiredResourceAccess << JSON
{
  "requiredResourceAccess": [
    {
      "resourceAppId": "${appId}",
      "resourceAccess": [
        {
            "id": "${userImpersonationScopeId}",
            "type": "Scope"
        },
        {
            "id": "${adminRoleId}",
            "type": "Role"
        }
      ]
    }
  ]
}
JSON
)

  # Utility function to add the required permissions.
  update_resource_access "$msGraphUri" "${automationAppObjectId}" "${appId}" "${automationApiAccess}"

  # Grant admin consent for the application scopes
  if [[ $grantAdminConsent -eq 1 ]]; then
      echo "Granting admin consent for \"${automationAppName}\" (App ID ${automationAppId})"
      automationSpId=$(az ad sp list --filter "appId eq '${automationAppId}'" --query '[0].id' --output tsv --only-show-errors)
      echo "Found Service Principal \"$automationSpId\" for \"${automationAppName}\"."

      grant_admin_consent "${automationSpId}" "${spId}" "${adminRoleId}"
      az ad app permission grant --id "$automationSpId" --api "$appId" --scope "user_impersonation" --only-show-errors
  fi
fi

# Set outputs in configuration file
yq -i ".authentication.api_client_id |= \"${appId}\"" config.yaml
yq -i ".authentication.api_client_secret |= \"${spPassword}\"" config.yaml
yq -i ".authentication.swagger_ui_client_id |= \"${uxAppId}\"" config.yaml

echo "api_client_id=\"${appId}\""
echo "api_client_secret=\"${spPassword}\""
echo "swagger_ui_client_id=\"${uxAppId}\""

if [[ $grantAdminConsent -eq 0 ]]; then
    echo -e "\e[96mNOTE: Make sure the API permissions of the app registrations have admin consent granted."
    echo -e "Run this script with flag -a to grant admin consent or configure the registrations in Azure Portal."
    echo -e "See APP REGISTRATIONS in documentation for more information.\e[0m"
fi
