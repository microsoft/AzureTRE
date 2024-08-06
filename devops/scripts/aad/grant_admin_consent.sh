#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

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
    local msGraphUri=""
    msGraphUri="$(az cloud show --query endpoints.microsoftGraphResourceId --output tsv)/v1.0"

    # test if enabled to avoid "Permission being assigned already exists on the object" error
    is_enabled=$(az rest --method GET \
      --uri "${msGraphUri}/servicePrincipals/${principalId}/appRoleAssignments" -o json \
      | jq -r ".value | map( select(.appRoleId==\"${appRoleId}\") ) | length")

    if [[ "$is_enabled" != "1" ]]; then
        data=$(jq -c . << JSON
        {
            "principalId": "${principalId}",
            "resourceId": "${resourceId}",
            "appRoleId": "${appRoleId}"
        }
JSON
    )
        az rest --method POST --uri "${msGraphUri}/servicePrincipals/${principalId}/appRoleAssignments" --body "${data}"
    fi
}
