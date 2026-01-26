#!/bin/bash
set -euo pipefail
# Use this for debug only
# set -o xtrace
# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for pre-creating the Workspace API Azure AD application registration.

Usage: $0 --name <workspace-name> --application-admin-clientid <client-id>

Options:
  -n,--name
      Required. Prefix for the Workspace API app registration name.
      The script appends " API" to keep naming consistent with Terraform.
  -y,--application-admin-clientid
      Required. Client ID of the application administrator (typically the TRE Core API
      app registration) that must be added as an owner of the workspace application.

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

declare appName=""
declare workspaceAppId=""
declare appObjectId=""
declare applicationAdminClientId=""
declare applicationAdminObjectId=""

declare currentUserId=""
declare msGraphUri=""

# Initialize parameters specified from command line
while [[ $# -gt 0 ]]; do
    case "$1" in
        -n|--name)
            appName=$2
            shift 2
        ;;
        -y|--application-admin-clientid)
          applicationAdminClientId=$2
          shift 2
        ;;
        *)
            echo "Invalid option: $1."
            show_usage
        ;;
    esac
done

###################################
# CHECK INCOMING PARAMETERS       #
###################################
if [[ -z "$appName" ]]; then
    echo "Please specify the application name." 1>&2
    show_usage
fi
appName="$appName API"
if [[ -z "$applicationAdminClientId" ]]; then
  echo "Please specify the application administrator client ID." 1>&2
  show_usage
fi

currentUserId=$(az ad signed-in-user show --query 'id' --output tsv --only-show-errors)
applicationAdminObjectId=$(az ad sp show --id "$applicationAdminClientId" --query id -o tsv --only-show-errors)
msGraphUri="$(az cloud show --query endpoints.microsoftGraphResourceId --output tsv)/v1.0"
tenant=$(az rest -m get -u "${msGraphUri}/domains" -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo -e "\e[96mEnsuring Workspace Application exists in the \"${tenant}\" Azure AD tenant.\e[0m"

# Load helper functions
# shellcheck disable=SC1091
source "${DIR}/get_existing_app.sh"
# shellcheck disable=SC1091
source "${DIR}/wait_for_new_app_registration.sh"

# Look for an existing app registration
existingApp=$(get_existing_app --name "${appName}")
if [[ -n ${existingApp} ]]; then
    appObjectId=$(echo "${existingApp}" | jq -r '.id')
    workspaceAppId=$(echo "${existingApp}" | jq -r '.appId')
    echo "Found existing app registration (AppId: ${workspaceAppId})"
fi

if [[ -z ${workspaceAppId} ]]; then
  echo "Creating \"${appName}\" app registration."
  appDefinition=$(jq -c . << JSON
{
  "displayName": "${appName}",
  "signInAudience": "AzureADMyOrg"
}
JSON
)

  workspaceAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${appDefinition}" --output tsv --query "appId")

  # Poll until the app registration is found in the listing.
  wait_for_new_app_registration "${workspaceAppId}"

  # Update to set the identifier URI.
  az ad app update --id "${workspaceAppId}" --identifier-uris "api://${workspaceAppId}" --only-show-errors
  appObjectId=$(az ad app show --id "${workspaceAppId}" --query "id" --output tsv --only-show-errors)
fi

if [[ -z ${appObjectId} ]]; then
  appObjectId=$(az ad app show --id "${workspaceAppId}" --query "id" --output tsv --only-show-errors)
fi

# Make the current user and the application administrator owners so Terraform can update later.
az ad app owner add --id "${workspaceAppId}" --owner-object-id "$currentUserId" --only-show-errors || true
az ad app owner add --id "${workspaceAppId}" --owner-object-id "$applicationAdminObjectId" --only-show-errors || true


# Output the application details
echo
echo "=========================================="
echo "Workspace Application Client ID: ${workspaceAppId}"
echo "=========================================="
echo

