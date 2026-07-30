#!/bin/bash
set -euo pipefail
# Use this for debug only
# set -o xtrace
# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for adding the Automation Admin Application as an owner to the Workspace Application.
This is required for the end-to-end tests to be able to create and manage workspaces.
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 --workspace-application-clientid <workspace-client-id>

Options:
    -w,--workspace-application-clientid    Required. Client ID of the workspace application to add automation admin to.

Note: The automation admin client ID is automatically read from config.yaml (authentication.test_account_client_id).
The automation admin will be assigned the WorkspaceOwner role.

USAGE
    exit 2
}

if ! command -v az &> /dev/null; then
    echo "This script requires Azure CLI" 1>&2
    exit 1
fi

if ! command -v yq &> /dev/null; then
    echo "This script requires yq" 1>&2
    exit 1
fi

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

declare workspaceAppClientId=""
declare automationAdminClientId=""
declare appRole="WorkspaceOwner"
declare msGraphUri=""

# Initialize parameters specified from command line
while [[ $# -gt 0 ]]; do
    case "$1" in
        -w|--workspace-application-clientid)
            workspaceAppClientId=$2
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
if [[ $(az account list --only-show-errors -o json | jq 'length') -eq 0 ]]; then
    echo "Please run az login -t <tenant> --allow-no-subscriptions"
    exit 1
fi

if [[ -z "$workspaceAppClientId" ]]; then
    echo "Please specify the workspace application client ID" 1>&2
    show_usage
fi

# Read automation admin client ID from config.yaml
if [[ -f "${DIR}/../../../config.yaml" ]]; then
    automationAdminClientId=$(yq '.authentication.test_account_client_id' "${DIR}/../../../config.yaml")
    if [[ "$automationAdminClientId" == "null" || -z "$automationAdminClientId" ]]; then
        echo "Could not find test_account_client_id in config.yaml. Please ensure the automation admin has been created." 1>&2
        echo "Run: make auth" 1>&2
        exit 1
    fi
    echo "Using automation admin client ID from config.yaml: ${automationAdminClientId}"
else
    echo "config.yaml not found. Please ensure you are running this script from the TRE root directory." 1>&2
    exit 1
fi

msGraphUri="$(az cloud show --query endpoints.microsoftGraphResourceId --output tsv)/v1.0"
tenant=$(az rest -m get -u "${msGraphUri}/domains" -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo -e "\e[96mAdding Automation Admin to Workspace Application in the \"${tenant}\" Azure AD tenant.\e[0m"

# Load helper functions
# shellcheck disable=SC1091
source "${DIR}/grant_admin_consent.sh"

# Get the service principal object IDs
echo "Getting automation admin service principal..."
automationAdminSpObjectId=$(az ad sp show --id "$automationAdminClientId" --query id -o tsv --only-show-errors)
if [[ -z "$automationAdminSpObjectId" ]]; then
    echo "Could not find service principal for automation admin client ID: $automationAdminClientId" 1>&2
    exit 1
fi

echo "Getting workspace application service principal..."
workspaceSpObjectId=$(az ad sp show --id "$workspaceAppClientId" --query id -o tsv --only-show-errors)
if [[ -z "$workspaceSpObjectId" ]]; then
    echo "Could not find service principal for workspace client ID: $workspaceAppClientId" 1>&2
    exit 1
fi

# Get the app role ID for the specified role
echo "Getting app role ID for role: $appRole"
workspaceApp=$(az ad app show --id "$workspaceAppClientId" --query "appRoles[?value=='$appRole']" -o json --only-show-errors)
if [[ $(echo "$workspaceApp" | jq length) -eq 0 ]]; then
    echo "Could not find app role '$appRole' in workspace application $workspaceAppClientId" 1>&2
    echo "Available app roles:"
    az ad app show --id "$workspaceAppClientId" --query "appRoles[].{value:value,displayName:displayName}" -o table --only-show-errors
    exit 1
fi

appRoleId=$(echo "$workspaceApp" | jq -r '.[0].id')
echo "Found app role ID: $appRoleId"

# Check if the role assignment already exists
echo "Checking if role assignment already exists..."
existing_assignment=$(az rest --method GET \
    --uri "${msGraphUri}/servicePrincipals/${automationAdminSpObjectId}/appRoleAssignments" -o json \
    | jq -r ".value | map(select(.appRoleId==\"${appRoleId}\" and .resourceId==\"${workspaceSpObjectId}\")) | length")

if [[ "$existing_assignment" == "1" ]]; then
    echo "Role assignment already exists. Automation Admin already has the $appRole role for this workspace application."
    exit 0
fi

# Grant the app role assignment
echo "Assigning $appRole role to Automation Admin..."
grant_admin_consent "$automationAdminSpObjectId" "$workspaceSpObjectId" "$appRoleId"

echo -e "\e[92mSuccessfully assigned $appRole role to Automation Admin for workspace application.\e[0m"
echo "Automation Admin Service Principal: $automationAdminSpObjectId"
echo "Workspace Application Service Principal: $workspaceSpObjectId"
echo "App Role: $appRole ($appRoleId)"
