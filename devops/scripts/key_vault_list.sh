#!/bin/bash

if [[ -z ${TRE_ID:-} ]]; then
    echo "TRE_ID environment variable must be set."
    exit 1
fi

echo "DEBUG: Check keyvault and secrets exist"

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

# add trap to remove deployment network exceptions on script exit
# shellcheck disable=SC1091
trap 'source "$script_dir/remove_deployment_network_exceptions.sh"' EXIT

# now add deployment network exceptions
# shellcheck disable=SC1091
source "$script_dir/add_deployment_network_exceptions.sh"

echo "az keyvault show"
az keyvault show --name "kv-${TRE_ID}"

echo "az keyvault secret list"
az keyvault secret list --vault-name "kv-${TRE_ID}"

echo "az keyvault secret list-deleted"
az keyvault secret list-deleted --vault-name "kv-${TRE_ID}"
