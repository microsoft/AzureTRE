#!/bin/bash
set -e

echo "# Generated environment variables from tf output"

jq -r '
    [
        {
            "path": "core_resource_group_name",
            "env_var": "RESOURCE_GROUP"
        },
        {
            "path": "app_gateway_name",
            "env_var": "APPLICATION_GATEWAY"
        },
        {
            "path": "static_web_storage",
            "env_var": "STORAGE_ACCOUNT"
        },
        {
            "path": "keyvault_name",
            "env_var": "KEYVAULT"
        },
        {
            "path": "azure_tre_fqdn",
            "env_var": "FQDN"
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
