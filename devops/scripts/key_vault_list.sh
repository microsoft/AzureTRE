#!/bin/bash

if [[ -z ${TRE_ID:-} ]]; then
    echo "TRE_ID environment variable must be set."
    exit 1
fi

echo "DEBUG: Check keyvault and secrets exist"

echo "az keyvault show"
az keyvault show --name kv-${TRE_ID}

echo "az keyvault secret list"
az keyvault secret list --vault-name kv-${TRE_ID}

echo "az keyvault secret list-deleted"
az keyvault secret list-deleted --vault-name kv-${TRE_ID}
