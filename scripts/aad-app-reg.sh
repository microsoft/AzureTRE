#!/bin/bash

# Setup Script
set -euo pipefail

usage()
{
	echo "Usage: $(basename $BASH_SOURCE) -n <app-name> [-r <reply-url>] [-a]" 1>&2
	echo 1>&2
	echo 'For example:' 1>&2
	echo "./$(basename $BASH_SOURCE) -n TRE -r https://mydre.region.cloudapp.azure.com/oidc-redirect" 1>&2
	echo 1>&2
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

declare tenant=$( az rest -m get -u https://graph.microsoft.com/v1.0/domains -o json | jq -r '.value[] | select(.isDefault == true) | .id')

echo "You are about to create App Registrations in the Azure AD Tenant ${tenant}."
read -p "Do you want to continue? (y/N)" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 0
fi

currentUserId=$(az ad signed-in-user show --query 'objectId' -o tsv)

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

# Is the API app already registered?
declare existingApiApp=$(get_existing_app "${appName} API")

if [[ -n ${existingApiApp} ]]; then
	apiAppObjectId=$(echo ${existingApiApp} | jq -r '.objectId')
	# Get existing ids of roles and scopes.
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
		"displayName": "TRE Userss",
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

function get_msgraph_scope() {
    local scope=$(az ad sp show --id ${msGraphAppId} --query "oauth2Permissions[?value=='$1'].id | [0]" -o tsv)
    jq -c . <<- JSON
    {
        "id": "${scope}",
        "type": "Scope"
    }
JSON
}

function get_msgraph_role() {

    local scope=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='$1'].id | [0]" -o tsv)
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

if [[ -n ${apiAppObjectId} ]]; then
	echo "Updating app ${apiAppObjectId}"
	az rest --method PATCH --uri "${msGraphUri}/applications/${apiAppObjectId}" --headers Content-Type=application/json --body "${apiApp}"
	apiAppId=$(az ad app show --id ${apiAppObjectId} --query "appId" -o tsv)
	echo "Updated App Registration updated with id ${apiAppId}"
else
	apiAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${apiApp}" -o tsv --query "appId")
	echo "New App Registration created with id ${apiAppId}"

	# Update to set the identifier URI.
	az ad app update --id ${apiAppId} --identifier-uris "api://${apiAppId}"
fi

# Make the current user an owner of the application.
az ad app owner add --id ${apiAppId} --owner-object-id $currentUserId

# See if a service principal already exists
spId=$(az ad sp list --filter "appId eq '${apiAppId}'" --query '[0].objectId' --output tsv)

# If not, create a new service principal
if [[ -z "$spId" ]]; then
	spId=$(az ad sp create --id ${apiAppId} --query 'objectId' --output tsv)
	echo "New Service Principal created with id $spId"
fi

# This tag ensures the app is listed in the "Enterprise applications"
az ad sp update --id $spId --set tags="['WindowsAzureActiveDirectoryIntegratedApp']"

# Grant admin consent on the required resource accesses (Graph API)
if [[ $grantAdminConsent -eq 1 ]]; then
	echo "Granting Admin Consent for ${apiAppId}"
	az ad app permission admin-consent --id ${apiAppId}
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

declare swaggerUIApp=$(jq -c . << JSON
{
	"displayName": "${appName} Swagger UI",
	"signInAudience": "AzureADMyOrg",
	"requiredResourceAccess": ${swaggerRequiredResourceAccess},
	"spa": {
		"redirectUris": [
			"http://localhost:8000/docs/oauth2-redirect"
		]
	}
}
JSON
)

echo "Register the \"${appName}Swagger UI\" application"

# Is the API app already registered?
declare existingSwaggerUIApp=$(get_existing_app "${appName} Swagger UI")
if [[ -n ${existingSwaggerUIApp} ]]; then
	swaggerUIAppObjectId=$(echo "${existingSwaggerUIApp}" | jq '.objectId')
	echo "Updating app ${swaggerUIAppObjectId}"
	az rest --method PATCH --uri "${msGraphUri}/applications/${swaggerUIAppObjectId}" --headers Content-Type=application/json --body "${swaggerUIApp}"
	swaggerAppId=$(az ad app show --id ${swaggerUIAppObjectId} --query "appId" -o tsv)
	echo "Updated App Registration with id ${swaggerAppId}"
else
	swaggerAppId=$(az rest --method POST --uri "${msGraphUri}/applications" --headers Content-Type=application/json --body "${swaggerUIApp}" -o tsv --query "appId")
	echo "New App Registration created with id ${swaggerAppId}"
fi

# Make the current user an owner of the application.
az ad app owner add --id ${swaggerAppId} --owner-object-id $currentUserId

# See if a service principal already exists
swaggerSpId=$(az ad sp list --filter "appId eq '${swaggerAppId}'" --query '[0].objectId' --output tsv)

# If not, create a new service principal
if [[ -z "$swaggerSpId" ]]; then
	swaggerSpId=$(az ad sp create --id ${swaggerAppId} --query 'objectId' --output tsv)
	echo "New Service Principal created with id $swaggerSpId"
fi

# Grant admin consent on the required resources
if [[ $grantAdminConsent -eq 1 ]]; then
	az ad app permission admin-consent --id ${swaggerAppId}
fi

echo "done"
