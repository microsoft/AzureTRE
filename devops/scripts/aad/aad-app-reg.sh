#!/bin/bash

# Setup Script
set -euo pipefail
# AZURE_CORE_OUTPUT=jsonc # force CLI output to JSON for the script (user can still change default for interactive usage in the dev container)

function show_usage()
{
    cat << USAGE

Utility script for creating app registrations required by Azure TRE.
By default script will create and configure two app registrations, one for the API and another for Swagger UI.
Alternatively using the -w flag will create an app registration for a TRE workspace
You must be logged in using Azure CLI with sufficient privileges to modify Azure Active Directory to run this script.

Usage: $0 -n <app-name> [-r <reply-url>] [-w] [-a] [-s] [--automation-account]

Options:
    -n,--name                   Required. The prefix for the app (registration) names e.g., "TRE", or "Workspace One".
    -w,--workspace              Create an app registration for a TRE workspace rather than the core TRE API and UI.
    -a,--admin-consent          Optional, but recommended. Grants admin consent for the app registrations, when this flag is set.
                                Requires directory admin privileges to the Azure AD in question.
    -s,--swaggerui-clientid     Optional, when -w and -a are specified the client ID of the swagger app must be provided.
    -r,--tre-url                TRE URL, used to construct auth redirection URLs for the UI and Swagger app.
    --automation-account        Create an app registration for automation (e.g. CI/CD) to use for registering bundles etc
                                Can be used with -a to apply admin consent
    --automation-clientid       Optional, when --workspace is specified the client ID of the automation account can be added to the TRE workspace.

Examples:
    1. $0 -n TRE -r https://mytre.region.cloudapp.azure.com -a

    2. $0 --name 'Workspace One' --tre-url https://mytre.region.cloudapp.azure.com --workspace

    Using an Automation account
    3. $0 --name 'TRE' --tre-url https://mytre.region.cloudapp.azure.com --admin-consent --automation-account
    4. $0 --name 'TRE - workspace 1' --workspace --admin-consent --swaggerui-clientid 7xxxxx-ccd8-4740-xxxx-a6ec01e10ab8 --automation-clientid 4xxxx-7dc5-xxxxx-bcff-xxxxx

    The GUIDS in example 4 are the outputs from example 3.

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
declare swaggerAppId=""
declare workspace=0
declare appName=""
declare treUrl=""
declare currentUserId=""
declare spId=""
declare createAutomationAccount=0
declare automationAppId=""
declare msGraphUri="https://graph.microsoft.com/v1.0"

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
        -w|--workspace)
            workspace=1
            shift 1
        ;;
        -s|--swaggerui-clientid)
            swaggerAppId=$2
            shift 2
        ;;
        -r|--tre-url)
            treUrl=$2
            shift 2
        ;;
        --automation-account)
            createAutomationAccount=1
            shift 1
        ;;
        --automation-clientid)
            automationAppId=$2
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
if [[ -z "$appName" ]]; then
    echo "Please specify the application name" 1>&2
    show_usage
fi

# if admin consent & workspace, but not swagger client id, show error
if [[ $workspace -eq 1 && $grantAdminConsent -eq 1 && -z "$swaggerAppId" ]]; then
    echo "When specifying --admin-consent and --workspace, please specify the swagger application client ID option" 1>&2
    show_usage
fi

if [[ $(az account list --only-show-errors -o json | jq 'length') -eq 0 ]]; then
    echo "Please run az login -t <tenant> --allow-no-subscriptions"
    exit 1
fi

currentUserId=$(az ad signed-in-user show --query 'objectId' --output tsv)
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

# Generate GUIDS
userRoleId=$(cat /proc/sys/kernel/random/uuid)
adminRoleId=$(cat /proc/sys/kernel/random/uuid)
researcherRoleId=$(cat /proc/sys/kernel/random/uuid)
ownerRoleId=$(cat /proc/sys/kernel/random/uuid)
apiUserImpersonationScopeID=$(cat /proc/sys/kernel/random/uuid)
apiAppObjectId=""

existingApiApp=$(get_existing_app --name "${appName} API")

if [[ -n ${existingApiApp} ]]; then
    apiAppObjectId=$(echo "${existingApiApp}" | jq -r '.objectId')

    # Get existing IDs of roles and scopes.
    if [[ $workspace -eq 0 ]]; then
      userRoleId=$(echo "$existingApiApp" | jq -r '.appRoles[] | select(.value == "TREUser").id')
      adminRoleId=$(echo "$existingApiApp" | jq -r '.appRoles[] | select(.value == "TREAdmin").id')
      if [[ -z "${userRoleId}" ]]; then userRoleId=$(cat /proc/sys/kernel/random/uuid); fi
      if [[ -z "${adminRoleId}" ]]; then adminRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    else
      researcherRoleId=$(echo "$existingApiApp" | jq -r '.appRoles[] | select(.value == "WorkspaceResearcher").id')
      ownerRoleId=$(echo "$existingApiApp" | jq -r '.appRoles[] | select(.value == "WorkspaceOwner").id')
      if [[ -z "${researcherRoleId}" ]]; then researcherRoleId=$(cat /proc/sys/kernel/random/uuid); fi
      if [[ -z "${ownerRoleId}" ]]; then ownerRoleId=$(cat /proc/sys/kernel/random/uuid); fi
    fi
    apiUserImpersonationScopeID=$(echo "$existingApiApp" | jq -r '.oauth2Permissions[] | select(.value == "user_impersonation").id')

    if [[ -z "${apiUserImpersonationScopeID}" ]]; then apiUserImpersonationScopeID=$(cat /proc/sys/kernel/random/uuid); fi
fi

appRoles=$(jq -c . << JSON
[
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
]
JSON
)

workspaceAppRoles=$(jq -c . << JSON
[
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
    }
]
JSON
)

oauth2PermissionScopes=$(jq -c . << JSON
[
    {
        "adminConsentDescription": "Allow the app to access the TRE API on behalf of the signed-in user.",
        "adminConsentDisplayName": "Access the TRE API on behalf of signed-in user",
        "id": "${apiUserImpersonationScopeID}",
        "isEnabled": true,
        "type": "User",
        "userConsentDescription": "Allow the app to access the TRE API on your behalf.",
        "userConsentDisplayName": "Access the TRE API",
        "value": "user_impersonation"
    }
]
JSON
)

workspaceOauth2PermissionScopes=$(jq -c . << JSON
[
    {
        "adminConsentDescription": "Allow the app to access the Workspace API on behalf of the signed-in user.",
        "adminConsentDisplayName": "Access the Workspace API on behalf of signed-in user",
        "id": "${apiUserImpersonationScopeID}",
        "isEnabled": true,
        "type": "User",
        "userConsentDescription": "Allow the app to access the Workspace API on your behalf.",
        "userConsentDisplayName": "Access the Workspace API",
        "value": "user_impersonation"
    }
]
JSON
)

msGraphAppId="00000003-0000-0000-c000-000000000000"
msGraphEmailScopeId="64a6cdd6-aab1-4aaf-94b8-3cc8405e90d0"
msGraphOpenIdScopeId="37f7f235-527c-4136-accd-4a02d197296e"
msGraphProfileScopeId="14dad69e-099b-42c9-810b-d002981feec1"
msGraphObjectId=$(az ad sp show --id ${msGraphAppId} --query "objectId" --output tsv)
directoryReadAllId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='Directory.Read.All'].id" --output tsv)
userReadAllId=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='User.Read.All'].id" --output tsv)
applicationReadWriteOwnedById=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='Application.ReadWrite.OwnedBy'].id" --output tsv)

roleUserReadAll=$(get_msgraph_role "User.Read.All" )
roleDirectoryReadAll=$(get_msgraph_role "Directory.Read.All" )
roleApplicationReadWriteOwnedBy=$(get_msgraph_role "Application.ReadWrite.OwnedBy" )

apiRequiredResourceAccess=$(jq -c . << JSON
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

workspaceRequiredResourceAccess=$(jq -c . << JSON
[
    {
        "resourceAppId": "${msGraphAppId}",
        "resourceAccess": [
            ${roleApplicationReadWriteOwnedBy}
        ]
    }
]
JSON
)

if [[ $workspace -eq 0 ]]; then
  apiApp=$(jq -c . << JSON
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

else
    apiApp=$(jq -c . << JSON
{
    "displayName": "${appName} API",
    "api": {
        "requestedAccessTokenVersion": 2,
        "oauth2PermissionScopes": ${workspaceOauth2PermissionScopes}
    },
    "appRoles": ${workspaceAppRoles},
    "signInAudience": "AzureADMyOrg",
    "requiredResourceAccess": ${workspaceRequiredResourceAccess},
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
fi

# Is the API app already registered?
if [[ -n ${apiAppObjectId} ]]; then
    echo "Updating API app registration with ID ${apiAppObjectId}"
    az rest --method PATCH --uri "${msGraphUri}/applications/${apiAppObjectId}" --headers Content-Type=application/json --body "${apiApp}"
    apiAppId=$(az ad app show --id "${apiAppObjectId}" --query "appId" --output tsv)
    echo "API app registration with ID ${apiAppId} updated"
else
    echo "Creating a new API app registration, ${appName} API"
    apiAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${apiApp}" --output tsv --query "appId")
    echo "AppId: ${apiAppId}"

    # Poll until the app registration is found in the listing.
    wait_for_new_app_registration "${apiAppId}"

    # Update to set the identifier URI.
    echo "Updating identifier URI 'api://${apiAppId}'"
    az ad app update --id "${apiAppId}" --identifier-uris "api://${apiAppId}"
fi

echo "Setting API permissions (email / profile / ipaddr)"
az ad app permission add --id "${apiAppId}" --api "${msGraphAppId}" \
  --api-permissions ${msGraphEmailScopeId}=Scope ${msGraphOpenIdScopeId}=Scope ${msGraphProfileScopeId}=Scope

# todo: [Issue 1352](https://github.com/microsoft/AzureTRE/issues/1352)
# echo "Updating redirect uri"
# Update app registration with redirect urls (SPA)
# az rest --method PATCH --uri "${msGraphUri}/applications/${apiAppObjectId}" \
#     --headers 'Content-Type=application/json' \
#     --body '{"spa":{"redirectUris":["https://localhost:8080"]}}'

# Make the current user an owner of the application.
az ad app owner add --id "${apiAppId}" --owner-object-id "$currentUserId"

# See if a service principal already exists
spId=$(az ad sp list --filter "appId eq '${apiAppId}'" --query '[0].objectId' --output tsv)

resetPassword=0

# If not, create a new service principal
if [[ -z "$spId" ]]; then
    spId=$(az ad sp create --id "${apiAppId}" --query 'objectId' --output tsv)
    echo "Creating a new service principal, for '${appName} API' app, with ID ${spId}"
    wait_for_new_service_principal "${spId}"
    az ad app owner add --id "${apiAppId}" --owner-object-id "${spId}"
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
    spPassword=$(az ad sp credential reset --name "${apiAppId}" --query 'password' --output tsv)
    echo "'${appName} API' app password (client secret): ${spPassword}"
fi

# This tag ensures the app is listed in "Enterprise applications"
az ad sp update --id "$spId" --set tags="['WindowsAzureActiveDirectoryIntegratedApp']"

# needed to make the API permissions change effective, this must be done after SP creation...
echo "running 'az ad app permission grant' to make changes effective"
az ad app permission grant --id "${apiAppId}" --api "${msGraphAppId}"

# If a workspace
if [[ "$workspace" -ne 0 ]]; then
  # Grant admin consent for the delegated workspace scopes
  if [[ "$grantAdminConsent" -eq 1 ]]; then
      echo "Granting admin consent for '${appName}' Workspace app (service principal ID ${spId}) - NOTE: Directory admin privileges required for this step"
      wait_for_new_service_principal "$spId"
      grant_admin_consent "$spId" "$msGraphObjectId" "$applicationReadWriteOwnedById"
  fi

  # The Swagger UI (which was created as part of the API) needs to also have access to this Workspace
  echo "Searching for existing Swagger application (${swaggerAppId})."
  existingSwaggerApp=$(get_existing_app --id "${swaggerAppId}")
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
                    "id": "${apiUserImpersonationScopeID}",
                    "type": "Scope"
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
    requiredResourceAccess=$(echo "${swaggerWorkspaceAccess}" | \
      jq '.requiredResourceAccess += .existingAccess | {requiredResourceAccess}')

    az rest --method PATCH \
      --uri "${msGraphUri}/applications/${swaggerObjectId}" \
      --headers Content-Type=application/json \
      --body "${requiredResourceAccess}"

  echo "Grant Swagger UI delegated access '${appName} API' (Client ID ${swaggerAppId})"
  az ad app permission grant --id "${swaggerAppId}" --api "${apiAppId}" --scope "user_impersonation"

else
  # Grant admin consent on the required resource accesses (Graph API)
  if [[ $grantAdminConsent -eq 1 ]]; then
      echo "Granting admin consent for '${appName} API' app (service principal ID ${spId}) - NOTE: Directory admin privileges required for this step"
      wait_for_new_service_principal "${spId}"
      grant_admin_consent "${spId}" "$msGraphObjectId" "${directoryReadAllId}"
      wait_for_new_service_principal "${spId}"
      grant_admin_consent "${spId}" "${msGraphObjectId}" "${userReadAllId}"
  fi

  # Now create the app for the Swagger UI
  scope_openid=$(get_msgraph_scope "openid")
  scope_offline_access=$(get_msgraph_scope "offline_access")

  swaggerRequiredResourceAccess=$(jq -c . << JSON
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
                "id": "${apiUserImpersonationScopeID}",
                "type": "Scope"
            }
        ]
    }
]
JSON
)

  redirectUris="\"http://localhost:8000/api/docs/oauth2-redirect\""

  if [[ -n ${treUrl} ]]; then
      echo "Adding reply/redirect URL \"${treUrl}\" to ${appName} Swagger UI app"
      redirectUris="${redirectUris}, \"${treUrl}\", \"${treUrl}/api/docs/oauth2-redirect\""
  fi

  swaggerUIApp=$(jq -c . << JSON
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

  echo "$swaggerUIApp"
  # Is the Swagger UI app already registered?
  existingSwaggerUIApp=$(get_existing_app --name "${appName} Swagger UI")

  if [[ -n ${existingSwaggerUIApp} ]]; then
      swaggerUIAppObjectId=$(echo "${existingSwaggerUIApp}" | jq -r '.objectId')
      echo "Updating Swagger UI app with ID ${swaggerUIAppObjectId}"
      az rest --method PATCH --uri "${msGraphUri}/applications/${swaggerUIAppObjectId}" --headers Content-Type=application/json --body "${swaggerUIApp}"
      swaggerAppId=$(az ad app show --id "${swaggerUIAppObjectId}" --query "appId" --output tsv)
      echo "Swagger UI app registration with ID ${swaggerAppId} updated"
  else
      swaggerAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${swaggerUIApp}" --output tsv --query "appId")
      echo "Creating a new app registration, ${appName} Swagger UI, with ID ${swaggerAppId}"

      # Poll until the app registration is found in the listing.
      wait_for_new_app_registration "${swaggerAppId}"
  fi

  # Make the current user an owner of the application.
  az ad app owner add --id "${swaggerAppId}" --owner-object-id "${currentUserId}"

  # See if a service principal already exists
  swaggerSpId=$(az ad sp list --filter "appId eq '${swaggerAppId}'" --query '[0].objectId' --output tsv)

  # If not, create a new service principal
  if [[ -z "$swaggerSpId" ]]; then
      swaggerSpId=$(az ad sp create --id "${swaggerAppId}" --query 'objectId' --output tsv)
      echo "Creating a new service principal, for ${appName} Swagger UI app, with ID $swaggerSpId"
      wait_for_new_service_principal "${swaggerSpId}"
  fi

  echo "Granting delegated access for ${appName} Swagger UI app (service principal ID ${swaggerSpId})"
  az ad app permission grant --id "$swaggerSpId" --api "$msGraphObjectId" --scope "offline_access openid"
  az ad app permission grant --id "$swaggerSpId" --api "$apiAppId" --scope "user_impersonation"
fi

automationApp=$(jq -c . << JSON
{
    "displayName": "${appName} Automation Admin App",
    "api": {
        "requestedAccessTokenVersion": 2
    },
    "signInAudience": "AzureADMyOrg",
    "requiredResourceAccess": [
        {
            "resourceAppId": "${apiAppId}",
            "resourceAccess": [
                {
                    "id": "${apiUserImpersonationScopeID}",
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

if [[ -n ${automationAppId} ]]; then
    echo "Searching for existing Automation application (${automationAppId})."
    existingAutomationApp=$(get_existing_app --id "${automationAppId}")

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
                    "id": "${apiUserImpersonationScopeID}",
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
    wait_for_new_app_registration "${automationAppId}"

    # Grant admin consent for the delegated workspace scopes
    if [[ $grantAdminConsent -eq 1 ]]; then
        echo "Granting admin consent for ${automationAppName} (App ID ${automationAppId})"
        az ad app permission admin-consent --id "${automationAppId}"
    fi
fi

if [[ $createAutomationAccount -ne 0 ]]; then
    # Create an App Registration to allow automation to authenticate to the API
    # E.g. to register bundles
    existingAutomationApp=$(get_existing_app --name "${appName} Automation Admin App")

    if [[ -n ${existingAutomationApp} ]]; then
        echo "Automation app exists - updating..."
        automationAppObjectId=$(echo "${existingAutomationApp}" | jq -r .objectId)
        automationAppId=$(echo "${existingAutomationApp}" | jq -r .appId)
        az rest --method PATCH --uri "${msGraphUri}/applications/${automationAppObjectId}" --headers Content-Type=application/json --body "${automationApp}"
    else
        echo "Automation app doesn't exist - creating..."

        automationAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${automationApp}" --output tsv --query "appId")
        echo "Creating a new automation admin app registration, '${appName} Automation Admin App', with ID ${automationAppId}"

        # Poll until the app registration is found in the listing.
        wait_for_new_app_registration "${automationAppId}"

        # Make the current user an owner of the application.
        az ad app owner add --id "${automationAppId}" --owner-object-id "${currentUserId}"
    fi

    # See if a service principal already exists
    automationSpId=$(az ad sp list --filter "appId eq '${automationAppId}'" --query '[0].objectId' --output tsv)

    resetPassword=0
    # If not, create a new service principal
    if [[ -z "$automationSpId" ]]; then
        automationSpId=$(az ad sp create --id "${automationAppId}" --query 'objectId' --output tsv)
        echo "Creating a new service principal, for '${appName}' Automation Admin App, with ID '$automationSpId'"
        wait_for_new_service_principal "${automationSpId}"
        resetPassword=1
    else
        echo "Service principal for the app already exists."
        echo "Existing passwords (client secrets) cannot be queried. To view the password it needs to be reset."
        read -p "Do you wish to reset the ${appName} Automation Admin App password (y/N)? " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            resetPassword=1
        fi
    fi

    automationSpPassword=""

    if [[ "$resetPassword" == 1 ]]; then
        # Reset the app password (client secret) and display it
        automationSpPassword=$(az ad sp credential reset --name "${automationAppId}" --query 'password' --output tsv)
        echo "${appName} Automation Admin App password (client secret): ${automationSpPassword}"
    fi

    # This tag ensures the app is listed in "Enterprise applications"
    az ad sp update --id "${automationSpId}" --set tags="['WindowsAzureActiveDirectoryIntegratedApp']"

  # Grant admin consent for the delegated workspace scopes
  # https://github.com/microsoft/AzureTRE/issues/1513
  # I've noticed that there can sometimes be a delay in the app having the permissions set
  # before we give admin-consent. If this occurs - rerun and it will work.
  if [[ $grantAdminConsent -eq 1 ]]; then
      echo "Granting admin consent for ${appName} Automation Admin App (ClientID ${automationAppId})"
      wait_for_new_app_registration "${automationAppId}"
      adminConsentResponse=$(az ad app permission admin-consent --id "${automationAppId}") || null
      if [ -z "${adminConsentResponse}" ]; then
          echo "Admin consent failed, trying once more: ${adminConsentResponse}"
          az ad app permission admin-consent --id "${automationAppId}"
      fi
  fi
fi


echo "Done"

# Output the variables for .env files
if [[ $workspace -eq 0 ]]; then
  cat << ENV_VARS

AAD_TENANT_ID="$(az account show --output json | jq -r '.tenantId')"

** Please copy the following variables to /templates/core/.env **

API_CLIENT_ID="${apiAppId}"
API_CLIENT_SECRET="${spPassword}"
SWAGGER_UI_CLIENT_ID="${swaggerAppId}"

ENV_VARS

else
  cat << ENV_VARS

AAD_TENANT_ID="$(az account show --output json | jq -r '.tenantId')"

** Please copy the following variables to /templates/core/.env **

WORKSPACE_API_CLIENT_ID="${apiAppId}"
WORKSPACE_API_CLIENT_SECRET="${spPassword}"

ENV_VARS
fi

if [[ $createAutomationAccount -eq 1 ]]; then
  cat << ENV_VARS
TEST_ACCOUNT_CLIENT_ID="${automationAppId}"
TEST_ACCOUNT_CLIENT_SECRET="${automationSpPassword}"

ENV_VARS

fi

if [[ $grantAdminConsent -eq 0 ]]; then
    echo "NOTE: Make sure the API permissions of the app registrations have admin consent granted."
    echo "Run this script with flag -a to grant admin consent or configure the registrations in Azure Portal."
    echo "See APP REGISTRATIONS in documentation for more information."
fi
