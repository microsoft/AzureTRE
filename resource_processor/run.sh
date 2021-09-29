#!/bin/bash

# Generate required configuration for Porter Azure plugin
if [[ -z "${MGMT_RESOURCE_GROUP_NAME}" ]]; then
  >&2 echo "Environment variable for TRE management resource group name missing"
fi

if [[ -z "${MGMT_STORAGE_ACCOUNT_NAME}" ]]; then
  >&2 echo "Environment variable for TRE management storage account name missing"
fi

cat > /root/.porter/config.toml << EOF
default-storage = "azurestorage"
no-logs = true

[[storage]]
name = "azurestorage"
plugin = "azure.table"

[storage.config]
account="${MGMT_STORAGE_ACCOUNT_NAME}"
resource-group="${MGMT_RESOURCE_GROUP_NAME}"
EOF

# Launch the runner
python -u vmss_porter/runner.py
