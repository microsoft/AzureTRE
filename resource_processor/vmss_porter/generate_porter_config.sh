#!/bin/bash

# Generates required configuration for Porter Azure plugin
# The output of this script should be appended to ~/.porter/config.toml

cat << EOF
default-storage = "azurestorage"

[[storage]]
name = "azurestorage"
plugin = "azure.blob"

[storage.config]
account="${MGMT_STORAGE_ACCOUNT_NAME}"
resource-group="${MGMT_RESOURCE_GROUP_NAME}"
EOF
