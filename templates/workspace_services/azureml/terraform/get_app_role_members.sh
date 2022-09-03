#!/bin/bash

set -euo pipefail

eval "$(jq -r '@sh "AUTH_CLIENT_ID=\(.auth_client_id) AUTH_CLIENT_SECRET=\(.auth_client_secret) AUTH_TENANT_ID=\(.auth_tenant_id)" WORSKPACE_CLIENT_ID=\(.workspace_client_id)"')"

az login --allow-no-subscriptions --service-principal --username "$AUTH_CLIENT_ID" --password "$AUTH_CLIENT_SECRET" --tenant "$AUTH_TENANT_ID"

spId=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/serviceprincipals?\$filter=appid eq '${WORSKPACE_CLIENT_ID}'" -o json | jq -r '.value[0].id')
principals=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/serviceprincipals/${spId}/appRoleAssignedTo?\$select=principalId" -o json | jq -r '.value[].principalId')

jq -n --arg principals "$principals" '{"principals":$principals}'
