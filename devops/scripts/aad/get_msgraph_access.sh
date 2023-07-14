#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

# Magic string for MSGraph
msGraphAppId="00000003-0000-0000-c000-000000000000"

function get_msgraph_scope() {
    oauthScope=$(az ad sp show --id ${msGraphAppId} --query "oauth2PermissionScopes[?value=='$1'].id | [0]" --output tsv --only-show-errors)
    jq -c . <<- JSON
    {
        "id": "${oauthScope}",
        "type": "Scope"
    }
JSON
}

function get_msgraph_role() {
    appRoleScope=$(az ad sp show --id ${msGraphAppId} --query "appRoles[?value=='$1'].id | [0]" --output tsv --only-show-errors)
    jq -c . <<- JSON
    {
        "id": "${appRoleScope}",
        "type": "Role"
    }
JSON
}
