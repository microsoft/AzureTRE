#!/bin/bash

# Generate required configuration for Porter Azure plugin
if [[ -z "${MGMT_RESOURCE_GROUP_NAME}" ]]; then
  >&2 echo "Environment variable for TRE management resource group name missing"
fi

if [[ -z "${MGMT_STORAGE_ACCOUNT_NAME}" ]]; then
  >&2 echo "Environment variable for TRE management storage account name missing"
fi

if [[ -z "${KEY_VAULT_NAME}" ]]; then
  >&2 echo "Environment variable for Key Vault name missing"
fi

# Documentation here: - https://github.com/vdice/porter-bundles/tree/master/azure-keyvault
cat > /root/.porter/config.toml << EOF
default-storage = "azurestorage"
default-secrets = "aad_auth"
no-logs = true

[[storage]]
name = "azurestorage"
plugin = "azure.table"

[storage.config]
account="${MGMT_STORAGE_ACCOUNT_NAME}"
resource-group="${MGMT_RESOURCE_GROUP_NAME}"

[[secrets]]
name = "aad_auth"
plugin = "azure.keyvault"

[secrets.config]
vault = "${KEY_VAULT_NAME}"
EOF

# Launch the runner
python -u vmss_porter/runner.py
