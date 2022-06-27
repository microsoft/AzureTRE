#!/bin/bash

# Setup Script
set -euo pipefail
# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for creating an application administrator for TRE. This is mandatory and is used
to manage AAD Application creation within TRE. This script is called when you run "make auth" and
the environment variable AUTO_WORKSPACE_APP_REGISTRATION determines the permission this identity has.
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 --name "MYTRE" --application-permission "Application.ReadWrite.OwnedBy" [--admin-consent]

Options:
    -n,--name                   Required. The prefix for the app (registration) names e.g., "TRE".
    -a,--admin-consent          Optional, but recommended. Grants admin consent for the app registrations, when this flag is set.
                                Requires directory admin privileges to the Azure AD in question.
    -p,--application-permission The API Permission that this identity will be granted.

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
declare spId=""
declare msGraphUri="https://graph.microsoft.com/v1.0"
declare appName=""
declare applicationPermission="Application.ReadWrite.OwnedBy"

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
        -p|--application-permission)
            applicationPermission=$2
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
appName="$appName Application Admin"
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
source "${DIR}/get_msgraph_access.sh"
# shellcheck disable=SC1091
source "${DIR}/create_or_update_service_principal.sh"

# Get an existing object if it's been created before.
appObjectId=""
existingApp=$(get_existing_app --name "${appName}") || null
if [ -n "${existingApp}" ]; then
    appObjectId=$(echo "${existingApp}" | jq -r '.objectId')
fi

# Get the Required Resource Scope/Role
msGraphAppId="00000003-0000-0000-c000-000000000000"
msGraphObjectId=$(az ad sp show --id ${msGraphAppId} --query "objectId" --output tsv --only-show-errors)

applicationPermissionId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='${applicationPermission}'].id" --output tsv --only-show-errors)
roleApplicationPermission=$(get_msgraph_role "${applicationPermission}")

appDefinition=$(jq -c . << JSON
{
    "displayName": "${appName}",
    "signInAudience": "AzureADMyOrg",
    "requiredResourceAccess": [
    {
        "resourceAppId": "${msGraphAppId}",
        "resourceAccess": [
            ${roleApplicationPermission}
        ]
    }]
}
JSON
)

# Is the app already registered?
if [[ -n ${appObjectId} ]]; then
    echo "Updating \"${appName}\" with ObjectId \"${appObjectId}\""
    az rest --method PATCH --uri "${msGraphUri}/applications/${appObjectId}" --headers Content-Type=application/json --body "${appDefinition}"
    appId=$(az ad app show --id "${appObjectId}" --query "appId" --output tsv --only-show-errors)
    echo "App registration with ID \"${appId}\" updated"
else
    echo "Creating a new app registration, \"${appName}\""
    appId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${appDefinition}" --output tsv --query "appId")

    # Poll until the app registration is found in the listing.
    wait_for_new_app_registration "${appId}"
fi

# Make the current user an owner of the application.
az ad app owner add --id "${appId}" --owner-object-id "$currentUserId" --only-show-errors

# Create a Service Principal for the app.
spPassword=$(create_or_update_service_principal "${appId}" "${appName}")
spId=$(az ad sp list --filter "appId eq '${appId}'" --query '[0].objectId' --output tsv --only-show-errors)

# needed to make the API permissions change effective, this must be done after SP creation...
echo
echo "Running 'az ad app permission grant' to make changes effective."
az ad app permission grant --id "${appId}" --api "${msGraphAppId}" --only-show-errors

# Grant admin consent on the required resource accesses (Graph API)
if [[ $grantAdminConsent -eq 1 ]]; then
    echo "Granting admin consent for '${appName}' app (service principal ID ${spId}) - NOTE: Directory admin privileges required for this step"
    wait_for_new_service_principal "${spId}"
    grant_admin_consent "${spId}" "$msGraphObjectId" "${applicationPermissionId}"
fi

cat << ENV_VARS

AAD_TENANT_ID="$(az account show --output json | jq -r '.tenantId')"

** Please copy the following variables to /templates/core/.env **

APPLICATION_ADMIN_CLIENT_ID="${appId}"
APPLICATION_ADMIN_CLIENT_SECRET="${spPassword}"

ENV_VARS

if [[ $grantAdminConsent -eq 0 ]]; then
    echo "NOTE: Make sure the API permissions of the app registrations have admin consent granted."
    echo "Run this script with flag -a to grant admin consent or configure the registrations in Azure Portal."
    echo "See APP REGISTRATIONS in documentation for more information."
fi
