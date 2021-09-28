#!/bin/bash

# Setup Script
set -euo pipefail

function usage()
{
    cat << USAGE

Utility script for creating app registrations required by Azure TRE.
The script will create and configure two app registrations, one for the API and another for Swagger UI.
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 -n <app-name> [-r <reply-url>] [-a]

Options:
    -n      Required. The prefix for the app (registration) names e.g., "TRE".
    -r      Reply/redirect URL, for the Swagger UI app, where the auth server sends the user after authorization.
    -a      Optional, but recommended. Grants admin consent for the app registrations, when this flag is set.
            Requires directory admin privileges to the Azure AD in question.

Example:
    $0 -n TRE -r https://mydre.region.cloudapp.azure.com/oidc-redirect -a

USAGE
    exit 1
}

if ! command -v az &> /dev/null; then
    echo "This script requires Azure CLI" 1>&2
    exit 1
fi

declare grantAdminConsent=0
declare appName=""
declare replyUrl=""
declare currentUserId=""
declare spId=""
declare msGraphUri="https://graph.microsoft.com/v1.0"

# Initialize parameters specified from command line
while getopts ":n:r:a" arg; do
    case "${arg}" in
        n)
            appName=${OPTARG}
        ;;
        r)
            replyUrl=${OPTARG}
        ;;
        a)
            grantAdminConsent=1
        ;;
        ?)
            echo "Invalid option: -${OPTARG}."
            exit 2
        ;;
    esac
done

if [[ -z "$appName" ]]; then
    echo "Please specify the application name" 1>&2
    usage
fi

if [[ $(az account list --only-show-errors -o json | jq 'length') -eq 0 ]]; then
    echo "Please run az login -t <tenant> --allow-no-subscriptions"
    exit 1
fi

# This function polls looking for an app registration with the given ID.
# If after the number of retries no app registration is found, the function exits.
function wait_for_new_app_registration()
{
    appId=$1
    retries=10
    counter=0
    objectId=$(az ad app list --filter "appId eq '${appId}'" --query '[0].objectId' --output tsv)

    while [[ -z $objectId && $counter -lt $retries ]]; do
        counter=$((counter+1))
        echo "Waiting for app registration with ID ${appId} to show up (${counter}/${retries})..."
        sleep 5
        objectId=$(az ad app list --filter "appId eq '${appId}'" --query '[0].objectId' --output tsv)
    done

    if [[ -z $objectId ]]; then
        echo "Failed"
        exit 1
    fi

    echo "App registration with ID ${appId} found"
}

# This function polls looking for a service principal with the given ID.
# If after the number of retries no app registration is found, the function exits.
function wait_for_new_service_principal()
{
    servicePrincipalId=$1
    retries=10
    counter=0
    output=$(az rest --method GET --uri https://graph.microsoft.com/v1.0/servicePrincipals/${servicePrincipalId} 2>/dev/null || true)

    while [[ -z $output && $counter -lt $retries ]]; do
        counter=$((counter+1))
        echo "Waiting for service principal with ID ${servicePrincipalId} to show up (${counter}/${retries})..."
        sleep 5
        output=$(az rest --method GET --uri https://graph.microsoft.com/v1.0/servicePrincipals/${servicePrincipalId} 2>/dev/null || true)
    done

    if [[ -z $output ]]; then
        echo "Failed"
        exit 1
    fi

    echo "Service principal with ID ${servicePrincipalId} found"
}

# Grants admin consent for the given app permission.
#
# Parameters:
#   1. principalId is the object ID of the service principal/managed application
#   2. resourceId is the object ID of the resource service principal (can in some cases be the same as principalId)
#   3. appRoleId is the ID of the permission
function grant_admin_consent()
{
    principalId=$1
    resourceId=$2
    appRoleId=$3

    data=$(jq -c . << JSON
    {
        "principalId": "${principalId}",
        "resourceId": "${resourceId}",
        "appRoleId": "${appRoleId}"
    }
JSON
    )

    az rest --method POST --uri ${msGraphUri}/servicePrincipals/${principalId}/appRoleAssignments --body ${data}
}

declare tenant=$(az rest -m get -u ${msGraphUri}/domains -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo "You are about to create app registrations in the Azure AD tenant \"${tenant}\"."
read -p "Do you want to continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 0
fi

currentUserId=$(az ad signed-in-user show --query 'objectId' --output tsv)

# Generate GUIDS
declare userRoleId=$(cat /proc/sys/kernel/random/uuid)
declare adminRoleId=$(cat /proc/sys/kernel/random/uuid)
declare workspaceReadId=$(cat /proc/sys/kernel/random/uuid)
declare workspaceWriteId=$(cat /proc/sys/kernel/random/uuid)

declare apiAppObjectId=""

function get_existing_app() {
    local existingApiApps=$(az ad app list --display-name "$1" -o json)

    if [[ $(echo ${existingApiApps} | jq 'length') -gt 1 ]]; then
        echo "There are more than one applications with the name \"$1\" already."
        exit 1
    fi

    if [[ $(echo ${existingApiApps} | jq 'length') -eq 1 ]]; then
        echo "${existingApiApps}" | jq -c '.[0]'
        return 0
    fi

    return 1
}

declare existingApiApp=$(get_existing_app "${appName} API")

if [[ -n ${existingApiApp} ]]; then
    apiAppObjectId=$(echo ${existingApiApp} | jq -r '.objectId')

    # Get existing IDs of roles and scopes.
    userRoleId=$(echo "$existingApiApp" | jq -r '.appRoles[] | select(.value == "TREUser").id')
    adminRoleId=$(echo "$existingApiApp" | jq -r '.appRoles[] | select(.value == "TREAdmin").id')
    workspaceReadId=$(echo "$existingApiApp" | jq -r '.oauth2Permissions[] | select(.value == "Workspace.Read").id')
    workspaceWriteId=$(echo "$existingApiApp" | jq -r '.oauth2Permissions[] | select(.value == "Workspace.Write").id')

    if [[ -z "${userRoleId}" ]]; then userRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${adminRoleId}" ]]; then adminRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${workspaceReadId}" ]]; then workspaceReadId=$(cat /proc/sys/kernel/random/uuid); fi
    if [[ -z "${workspaceWriteId}" ]]; then workspaceWriteId=$(cat /proc/sys/kernel/random/uuid); fi
fi

declare appRoles=$(jq -c . << JSON
[
    {
        "id": "${userRoleId}",
        "allowedMemberTypes": [ "User" ],
        "description": "Provides access to the ${appName} application.",
        "displayName": "TRE Users",
        "isEnabled": true,
        "origin": "Application",
        "value": "TREUser"
    },
    {
        "id": "${adminRoleId}",
        "allowedMemberTypes": [ "User" ],
        "description": "Provides resource administrator access to the ${appName}.",
        "displayName": "TRE Administrators",
        "isEnabled": true,
        "origin": "Application",
        "value": "TREAdmin"
    }
]
JSON
)

declare oauth2PermissionScopes=$(jq -c . << JSON
[
    {
        "adminConsentDescription": "Allow the app to get information about the ${appName} workspaces on behalf of the signed-in user.",
        "adminConsentDisplayName": "List and Get ${appName} Workspaces",
        "id": "${workspaceReadId}",
        "isEnabled": true,
        "type": "User",
        "userConsentDescription": "Allow the app to get information about the ${appName} workspaces on your behalf.",
        "userConsentDisplayName": "Get the ${appName} Workspaces you have access to",
        "value": "Workspace.Read"
    },
    {
        "adminConsentDescription": "Allow the app to create, update or delete ${appName} workspaces on behalf of the signed-in user.",
        "adminConsentDisplayName": "Modify ${appName} Workspaces",
        "id": "${workspaceWriteId}",
        "isEnabled": true,
        "type": "User",
        "userConsentDescription": "Allow the app to create, update or delete ${appName} workspaces on your behalf.",
        "userConsentDisplayName": "Modify ${appName} Workspaces for you",
        "value": "Workspace.Write"
    }
]
JSON
)

declare msGraphAppId="00000003-0000-0000-c000-000000000000"
declare msGraphObjectId=$(az ad sp show --id ${msGraphAppId} --query "objectId" --output tsv)
declare directoryReadAllId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='Directory.Read.All'].id" --output tsv)
declare userReadAllId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='User.Read.All'].id" --output tsv)

function get_msgraph_scope() {
    local scope=$(az ad sp show --id ${msGraphAppId} --query "oauth2Permissions[?value=='$1'].id | [0]" --output tsv)
    jq -c . <<- JSON
    {
        "id": "${scope}",
        "type": "Scope"
    }
JSON
}

function get_msgraph_role() {
    local scope=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='$1'].id | [0]" --output tsv)
    jq -c . <<- JSON
    {
        "id": "${scope}",
        "type": "Role"
    }
JSON
}

declare roleUserReadAll=$(get_msgraph_role "User.Read.All" )
declare roleDirectoryReadAll=$(get_msgraph_role "Directory.Read.All" )

declare apiRequiredResourceAccess=$(jq -c . << JSON
[
    {
        "resourceAppId": "${msGraphAppId}",
        "resourceAccess": [
            ${roleUserReadAll},
            ${roleDirectoryReadAll}
        ]
    }
]
JSON
)

declare apiApp=$(jq -c . << JSON
{
    "displayName": "${appName} API",
    "api": {
        "requestedAccessTokenVersion": 2,
        "oauth2PermissionScopes": ${oauth2PermissionScopes}
    },
    "appRoles": ${appRoles},
    "signInAudience": "AzureADMyOrg",
    "requiredResourceAccess": ${apiRequiredResourceAccess}
}
JSON
)

# Is the API app already registered?
if [[ -n ${apiAppObjectId} ]]; then
    echo "Updating API app registration with ID ${apiAppObjectId}"
    az rest --method PATCH --uri "${msGraphUri}/applications/${apiAppObjectId}" --headers Content-Type=application/json --body "${apiApp}"
    apiAppId=$(az ad app show --id ${apiAppObjectId} --query "appId" --output tsv)
    echo "API app registration with ID ${apiAppId} updated"
else
    apiAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${apiApp}" --output tsv --query "appId")
    echo "Creating a new API app registration, ${appName} API, with ID ${apiAppId}"

    # Poll until the app registration is found in the listing.
    wait_for_new_app_registration $apiAppId

    # Update to set the identifier URI.
    az ad app update --id ${apiAppId} --identifier-uris "api://${apiAppId}"
fi

# Make the current user an owner of the application.
az ad app owner add --id ${apiAppId} --owner-object-id $currentUserId

# See if a service principal already exists
spId=$(az ad sp list --filter "appId eq '${apiAppId}'" --query '[0].objectId' --output tsv)

resetPassword=0

# If not, create a new service principal
if [[ -z "$spId" ]]; then
    spId=$(az ad sp create --id ${apiAppId} --query 'objectId' --output tsv)
    echo "Creating a new service principal, for ${appName} API app, with ID $spId"
    wait_for_new_service_principal $spId
    resetPassword=1
else
    echo "Service principal for the app already exists."
    echo "Existing passwords (client secrets) cannot be queried. To view the password it needs to be reset."
    read -p "Do you wish to reset the ${appName} API app password (y/N)? " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        resetPassword=1
    fi
fi

spPassword=""

if [[ "$resetPassword" == 1 ]]; then
    # Reset the app password (client secret) and display it
    spPassword=$(az ad sp credential reset --name ${apiAppId} --query 'password' --output tsv)
    echo "${appName} API app password (client secret): ${spPassword}"
fi

# This tag ensures the app is listed in "Enterprise applications"
az ad sp update --id $spId --set tags="['WindowsAzureActiveDirectoryIntegratedApp']"

# Grant admin consent on the required resource accesses (Graph API)
if [[ $grantAdminConsent -eq 1 ]]; then
    echo "Granting admin consent for ${appName} API app (service principal ID ${spId}) - NOTE: Directory admin privileges required for this step"
    grant_admin_consent $spId $msGraphObjectId $directoryReadAllId
    grant_admin_consent $spId $msGraphObjectId $userReadAllId
fi

# Now create the app for the Swagger UI
declare scope_openid=$(get_msgraph_scope "openid")
declare scope_offline_access=$(get_msgraph_scope "offline_access")

declare swaggerRequiredResourceAccess=$(jq -c . << JSON
[
    {
        "resourceAppId": "00000003-0000-0000-c000-000000000000",
        "resourceAccess": [
            ${scope_openid},
            ${scope_offline_access}
        ]
    },
    {
        "resourceAppId": "${apiAppId}",
        "resourceAccess": [
            {
                "id": "${workspaceReadId}",
                "type": "Scope"
            },
            {
                "id": "${workspaceWriteId}",
                "type": "Scope"
            }
        ]
    }
]
JSON
)

redirectUris="\"http://localhost:8000/docs/oauth2-redirect\""

if [[ -n ${replyUrl} ]]; then
    echo "Adding reply/redirect URL \"${replyUrl}\" to ${appName} Swagger UI app"
    redirectUris="${redirectUris}, \"${replyUrl}\""
fi

declare swaggerUIApp=$(jq -c . << JSON
{
    "displayName": "${appName} Swagger UI",
    "signInAudience": "AzureADMyOrg",
    "requiredResourceAccess": ${swaggerRequiredResourceAccess},
    "spa": {
        "redirectUris": [
            ${redirectUris}
        ]
    }
}
JSON
)

# Is the Swagger UI app already registered?
declare existingSwaggerUIApp=$(get_existing_app "${appName} Swagger UI")

if [[ -n ${existingSwaggerUIApp} ]]; then
    swaggerUIAppObjectId=$(echo "${existingSwaggerUIApp}" | jq -r '.objectId')
    echo "Updating Swagger UI app with ID ${swaggerUIAppObjectId}"
    az rest --method PATCH --uri "${msGraphUri}/applications/${swaggerUIAppObjectId}" --headers Content-Type=application/json --body "${swaggerUIApp}"
    swaggerAppId=$(az ad app show --id ${swaggerUIAppObjectId} --query "appId" --output tsv)
    echo "Swagger UI app registration with ID ${swaggerAppId} updated"
else
    swaggerAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${swaggerUIApp}" --output tsv --query "appId")
    echo "Creating a new app registration, ${appName} Swagger UI, with ID ${swaggerAppId}"

    # Poll until the app registration is found in the listing.
    wait_for_new_app_registration $swaggerAppId
fi

# Make the current user an owner of the application.
az ad app owner add --id ${swaggerAppId} --owner-object-id $currentUserId

# See if a service principal already exists
swaggerSpId=$(az ad sp list --filter "appId eq '${swaggerAppId}'" --query '[0].objectId' --output tsv)

# If not, create a new service principal
if [[ -z "$swaggerSpId" ]]; then
    swaggerSpId=$(az ad sp create --id ${swaggerAppId} --query 'objectId' --output tsv)
    echo "Creating a new service principal, for ${appName} Swagger UI app, with ID $swaggerSpId"
    wait_for_new_service_principal $swaggerSpId
fi

# Grant admin consent for the delegated scopes
if [[ $grantAdminConsent -eq 1 ]]; then
    echo "Granting admin consent for ${appName} Swagger UI app (service principal ID ${swaggerSpId})"
    az ad app permission grant --id $swaggerSpId --api $msGraphObjectId --scope "offline_access openid"
    az ad app permission grant --id $swaggerSpId --api $apiAppId --scope "Workspace.Read Workspace.Write"
fi

echo "Done"

# Output the variables for .env files
cat << ENV_VARS

Variables:

AAD_TENANT_ID=$(az account show | jq -r '.tenantId')
API_CLIENT_ID=${apiAppId}
API_CLIENT_SECRET=${spPassword}
SWAGGER_UI_CLIENT_ID=${swaggerAppId}

ENV_VARS

if [[ $grantAdminConsent -eq 0 ]]; then
    echo "NOTE: Make sure the API permissions of the app registrations have admin consent granted."
    echo "Run this script with flag -a to grant admin consent or configure the registrations in Azure Portal."
    echo "See APP REGISTRATIONS in documentation for more information."
fi
