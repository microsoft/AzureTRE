#!/bin/bash

# Generates required configuration for Porter Azure plugin
# The output of this script should be appended to ~/.porter/config.toml

if [[ -z "${MGMT_RESOURCE_GROUP_NAME}" ]]; then
  >&2 echo "Environment variable for TRE management resource group name missing"
  exit 1
fi

if [[ -z "${MGMT_STORAGE_ACCOUNT_NAME}" ]]; then
  >&2 echo "Environment variable for TRE management storage account name missing"
  exit 1
fi

cat << EOF
default-storage = "azurestorage"

[[storage]]
name = "azurestorage"
plugin = "azure.blob"

[storage.config]
account="${MGMT_STORAGE_ACCOUNT_NAME}"
resource-group="${MGMT_RESOURCE_GROUP_NAME}"
EOF
