#!/bin/bash
set -e

echo "# Generated environment variables from tf output"

jq -r '
    [
        {
            "path": "fqdn",
            "env_var": "FQDN"
        },
        {
            "path": "application_gateway",
            "env_var": "APPLICATION_GATEWAY"
        },
        {
            "path": "storage_account_id",
            "env_var": "STORAGE_ACCOUNT_ID"
        },
        {
            "path": "storage_account_name",
            "env_var": "STORAGE_ACCOUNT_NAME"
        },
        {
            "path": "resource_group_name",
            "env_var": "RESOURCE_GROUP_NAME"
        },
        {
            "path": "keyvault",
            "env_var": "KEYVAULT"
        }
    ]
        as $env_vars_to_extract
    |
    with_entries(
        select (
            .key as $a
            |
            any( $env_vars_to_extract[]; .path == $a)
        )
        |
        .key |= . as $old_key | ($env_vars_to_extract[] | select (.path == $old_key) | .env_var)
    )
    |
    to_entries
    |
    map("\(.key)=\"\(.value.value)\"")
    |
    .[]
    ' | sed "s/\"/'/g" # replace double quote with single quote to handle special chars
