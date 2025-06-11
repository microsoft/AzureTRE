#!/bin/bash

#
# Add an exception to the TRE management ACR by making it public for deployment, and remove it on script exit.
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"

# Global variable to capture underlying error
LAST_PUBLIC_ACCESS_ERROR=""

function mgmtacr_enable_public_access() {
local RESOURCE_GROUP
RESOURCE_GROUP=$(get_resource_group_name)

local ACR_NAME
ACR_NAME=$(get_acr_name)

# Check that the acr exists before making changes
if ! does_acr_exist "$ACR_NAME"; then
    echo -e "Error: ACR $ACR_NAME does not exist.\n" >&2
    exit 1
fi

echo -e "\nEnabling public access on acr $ACR_NAME"

# Enable public network access with explicit default action allow
az acr update --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --public-network-enabled true --default-action Allow --output none

for ATTEMPT in {1..10}; do
    if is_public_access_enabled "$RESOURCE_GROUP" "$ACR_NAME"; then
    echo -e " ACR $ACR_NAME is now publicly accessible\n"
    return
    fi

    echo " Unable to confirm public access on ACR $ACR_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
done

echo -e "Error: Could not enable public access for $ACR_NAME after 10 attempts.\n"
echo -e "$LAST_PUBLIC_ACCESS_ERROR\n"
exit 1
}

function mgmtacr_disable_public_access() {
local RESOURCE_GROUP
RESOURCE_GROUP=$(get_resource_group_name)

local ACR_NAME
ACR_NAME=$(get_acr_name)

# Check that the ACR exists before making changes
if ! does_acr_exist "$ACR_NAME"; then
    echo -e "Error: ACR $ACR_NAME does not exist.\n" >&2
    exit 1
fi

echo -e "\nDisabling public access on ACR $ACR_NAME"

# Disable public network access with explicit default action deny
az acr update --resource-group "$RESOURCE_GROUP" --name "$ACR_NAME" --public-network-enabled false --default-action Deny --output none

for ATTEMPT in {1..10}; do
    if ! is_public_access_enabled "$RESOURCE_GROUP" "$ACR_NAME"; then
    echo -e " Public access has been disabled successfully\n"
    return
    fi

    echo " Unable to confirm public access is disabled on sACR $ACR_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
done

echo -e "Error: Could not disable public access for $ACR_NAME after 10 attempts.\n"
exit 1
}

function get_resource_group_name() {
if [[ -z "${TF_VAR_mgmt_resource_group_name:-}" ]]; then
    echo -e "Error: TF_VAR_mgmt_resource_group_name is not set\nExiting...\n" >&2
    exit 1
fi
echo "$TF_VAR_mgmt_resource_group_name"
}

function get_acr_name() {
if [[ -z "${TF_VAR_acr_name:-}" ]]; then
    echo -e "Error: TF_VAR_acr_name is not set\nExiting...\n" >&2
    exit 1
fi
echo "$TF_VAR_acr_name"
}

function does_acr_exist() {
[[ -n "$(az acr show --name "$1" --query "id" --output tsv)" ]]
}

function is_public_access_enabled() {
local RESOURCE_GROUP="$1"
local ACR_NAME="$2"
LAST_PUBLIC_ACCESS_ERROR=""

# Check if public network access is enabled for ACR
local public_access
public_access=$(az acr show --name "$ACR_NAME" --query "publicNetworkAccess" --output tsv 2>&1)

if [[ "$public_access" == "Enabled" ]]; then
    return 0  # Public access is enabled
else
    LAST_PUBLIC_ACCESS_ERROR="$public_access"
    return 1  # Public access is disabled
fi

}

# Setup the trap to disable public access on exit
add_exit_trap "mgmtacr_disable_public_access"

# Enable public access for deployment
mgmtacr_enable_public_access "$@" 
