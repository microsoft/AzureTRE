#!/bin/bash

set -euo pipefail

eval "$(jq -r '@sh "AUTH_CLIENT_ID=\(.auth_client_id) AUTH_CLIENT_SECRET=\(.auth_client_secret) AUTH_TENANT_ID=\(.auth_tenant_id) WORSKPACE_CLIENT_ID=\(.workspace_client_id)"')"

az login --allow-no-subscriptions --service-principal --username "$AUTH_CLIENT_ID" --password "$AUTH_CLIENT_SECRET" --tenant "$AUTH_TENANT_ID" > /dev/null

# get the service principal object id
sp=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/serviceprincipals?\$filter=appid eq '${WORSKPACE_CLIENT_ID}'" -o json)
spId=$(echo "$sp" | jq -r '.value[0].id')

# filter to the Workspace Researcher Role
workspaceResearcherRoleId=$(echo "$sp" | jq -r '.value[0].appRoles[] | select(.value == "WorkspaceResearcher") | .id')
principals=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/serviceprincipals/${spId}/appRoleAssignedTo" -o json | jq -r --arg workspaceResearcherRoleId "${workspaceResearcherRoleId}" '.value[] | select(.appRoleId == $workspaceResearcherRoleId) | .principalId')

jq -n --arg principals "$principals" '{"principals":$principals}'
