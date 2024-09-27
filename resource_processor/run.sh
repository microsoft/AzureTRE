#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# Generate required configuration for Porter Azure plugin

# TODO: Remove porter v0 https://github.com/microsoft/AzureTRE/issues/2990
# Documentation here: - https://github.com/vdice/porter-bundles/tree/master/azure-keyvault
cat > /"${PORTER_HOME_V0}"/config.toml << EOF
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

# TODO: Remove porter v0 https://github.com/microsoft/AzureTRE/issues/2990
echo "Azure cli login..."
az cloud set --name "${AZURE_ENVIRONMENT}"
az login --identity -u "${VMSS_MSI_ID}"

echo "Checking if porter v0 state exists..."
exists=$(az storage table exists --account-name "${MGMT_STORAGE_ACCOUNT_NAME}" --name "porter" --auth-mode "login" --output tsv)
if [ "${exists}" = "True" ]; then
  echo "v0 state exists. Checking if migration was completed once before..."
  migration_complete_container_name="porter-migration-completed"
  exists=$(az storage container exists --account-name "${MGMT_STORAGE_ACCOUNT_NAME}" --name "${migration_complete_container_name}" --auth-mode "login" --output tsv)
  if [ "${exists}" = "False" ]; then
      echo "${migration_complete_container_name} container doesn't exist. Running porter migration..."
      porter storage migrate --old-home "${PORTER_HOME_V0}" --old-account "azurestorage"
      echo "Porter migration complete. Creating ${migration_complete_container_name} container to prevent migrating again in the future..."
      az storage container create --account-name "${MGMT_STORAGE_ACCOUNT_NAME}" --name "${migration_complete_container_name}" --auth-mode "login" --fail-on-exist
      echo "Migration is done."
  else
      echo "${migration_complete_container_name} container is present. Skipping porter migration."
  fi
else
  echo "Porter v0 state doesn't exist."
fi

# Launch the runner
echo "Starting resource processor..."
python -u vmss_porter/runner.py
