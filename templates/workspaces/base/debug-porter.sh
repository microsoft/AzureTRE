#!/bin/bash
set -e

# This script is not used and is left here for you to debug the creation of the workspace
# at a Porter level without using the Resource Processor

# shellcheck disable=SC1091
. .env
. ../../../devops/scripts/load_env.sh ../../../devops/.env
. ../../../devops/scripts/load_env.sh ../../../templates/core/.env

porter install -p ./parameters.json \
  -c ./debug-aad-auth.json \
  -c /workspaces/AzureTRE/resource_processor/vmss_porter/azure.json

read -p "Would you like to uninstall this porter bundle? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    exit 0
fi

porter uninstall -p ./parameters.json \
  -c ./debug-aad-auth.json \
  -c /workspaces/AzureTRE/resource_processor/vmss_porter/azure.json
