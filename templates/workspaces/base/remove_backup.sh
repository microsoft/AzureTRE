#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

# Runs during workspace 'uninstall', before Terraform destroys the workspace. Azure
# secure-by-default keeps soft delete enabled on Recovery Services Vaults, so Terraform
# cannot tear down a vault that still has (soft-)protected items.
#   delete_backups_on_uninstall=true  - stop protection with data deletion, unregister
#       the backup containers and delete the vault, then let Terraform destroy the
#       workspace (including its resource group).
#   delete_backups_on_uninstall=false - stop protection but keep the recovery points,
#       then remove the vault, its resource group and the backup resources from the
#       Terraform state so they are retained.

MGMT_RESOURCE_GROUP_NAME=$1
MGMT_STORAGE_ACCOUNT_NAME=$2
TF_STATE_CONTAINER_NAME=$3
TRE_ID=$4
WORKSPACE_ID=$5
ENABLE_BACKUP=$6
DELETE_BACKUPS=$7
WORKSPACE_SUBSCRIPTION_ID=${8:-}

ENABLE_BACKUP=$(echo "${ENABLE_BACKUP}" | tr '[:upper:]' '[:lower:]')
DELETE_BACKUPS=$(echo "${DELETE_BACKUPS}" | tr '[:upper:]' '[:lower:]')

if [ "${ENABLE_BACKUP}" != "true" ]; then
  echo "Backup is not enabled for this workspace - nothing to do."
  exit 0
fi

short_workspace_id="${WORKSPACE_ID: -4}"
vault_name="arsv-${TRE_ID}-ws-${short_workspace_id}"
# The vault lives in the workspace resource group.
vault_resource_group="rg-${TRE_ID}-ws-${short_workspace_id}"

echo "Authenticating using the managed identity..."
az login --identity --output none
# When the workspace is not deployed to a dedicated subscription it lives in the same
# subscription as the rest of the TRE (ARM_SUBSCRIPTION_ID). Select the subscription
# explicitly so the vault lookup below does not run against the managed identity's
# arbitrary default subscription.
target_subscription_id="${WORKSPACE_SUBSCRIPTION_ID:-${ARM_SUBSCRIPTION_ID:-}}"
if [ -n "${target_subscription_id}" ]; then
  az account set --subscription "${target_subscription_id}"
fi

# If the vault no longer exists there is nothing to clean up. Only a genuine
# 'not found' response is treated as "nothing to do" - any other error (for example
# a permissions or throttling problem) must fail the script so we do not silently skip
# the cleanup and leave the workspace stuck in a 'Deleting' state.
if vault_show_error="$(az backup vault show --name "${vault_name}" --resource-group "${vault_resource_group}" --output none 2>&1)"; then
  echo "Recovery Services Vault ${vault_name} found in resource group ${vault_resource_group}."
elif echo "${vault_show_error}" | grep -qiE "ResourceNotFound|ResourceGroupNotFound|was not found|could not be found|does not exist"; then
  echo "Recovery Services Vault ${vault_name} was not found - nothing to do."
  exit 0
else
  echo "Error querying Recovery Services Vault ${vault_name}: ${vault_show_error}" >&2
  exit 1
fi

if [ "${DELETE_BACKUPS}" == "true" ]; then
  delete_backup_data="true"
  echo "delete_backups_on_uninstall is enabled - protection will be stopped, backups deleted and the vault removed."
else
  delete_backup_data="false"
  echo "delete_backups_on_uninstall is disabled - protection will be stopped but the recovery points and vault retained."
fi

backup_management_types=(AzureStorage AzureIaasVM)

stop_protection() {
  local bmt=$1 items attempt
  if ! items=$(az backup item list --vault-name "${vault_name}" --resource-group "${vault_resource_group}" \
    --backup-management-type "${bmt}" --query "[].[properties.containerName, name, properties.protectionState]" --output tsv); then
    echo "Error: failed to list ${bmt} backup items in vault ${vault_name}. Aborting so the uninstall can be retried." >&2
    exit 1
  fi
  [ -z "${items}" ] && return 0
  while IFS=$'\t' read -r container_name item_name protection_state; do
    [ -z "${item_name}" ] && continue
    # Already stopped - keep the script idempotent across the second pass and re-runs.
    [ "${protection_state}" == "ProtectionStopped" ] && continue
    for attempt in $(seq 1 5); do
      echo "Disabling protection for '${item_name}' (delete-backup-data=${delete_backup_data}, attempt ${attempt})..."
      if az backup protection disable --vault-name "${vault_name}" --resource-group "${vault_resource_group}" \
        --backup-management-type "${bmt}" --container-name "${container_name}" --item-name "${item_name}" \
        --delete-backup-data "${delete_backup_data}" --yes --output none; then
        break
      fi
      if [ "${attempt}" -eq 5 ]; then
        echo "Error: could not disable protection for '${item_name}' after ${attempt} attempts. Aborting so the uninstall can be retried." >&2
        exit 1
      fi
      sleep 15
    done
  done <<< "${items}"
}

for bmt in "${backup_management_types[@]}"; do
  stop_protection "${bmt}"
done

# Remove any Azure Backup lock on the workspace storage account. Only locks scoped
# directly to the account are removed; the scope match is case-insensitive because
# Azure lower-cases segments of the lock id.
subscription_id=$(az account show --query "id" --output tsv)
storage_account_id="/subscriptions/${subscription_id}/resourceGroups/${vault_resource_group}/providers/Microsoft.Storage/storageAccounts/stgws${short_workspace_id}"
storage_account_id_lower=$(echo "${storage_account_id}" | tr '[:upper:]' '[:lower:]')
if ! lock_ids=$(az lock list --resource "${storage_account_id}" --query "[].id" --output tsv); then
  echo "Error: failed to list resource locks on the workspace storage account. Aborting so the uninstall can be retried." >&2
  exit 1
fi
while IFS= read -r lock_id; do
  [ -z "${lock_id}" ] && continue
  case "$(echo "${lock_id}" | tr '[:upper:]' '[:lower:]')" in
    "${storage_account_id_lower}/"*)
      echo "Deleting resource lock ${lock_id}..."
      az lock delete --ids "${lock_id}" --output none || echo "Warning: could not delete lock ${lock_id}."
      ;;
  esac
done <<< "${lock_ids}"

for bmt in "${backup_management_types[@]}"; do
  stop_protection "${bmt}"
done

pushd terraform > /dev/null

terraform init -input=false -backend=true -reconfigure \
  -backend-config="resource_group_name=${MGMT_RESOURCE_GROUP_NAME}" \
  -backend-config="storage_account_name=${MGMT_STORAGE_ACCOUNT_NAME}" \
  -backend-config="container_name=${TF_STATE_CONTAINER_NAME}" \
  -backend-config="key=${TRE_ID}-ws-${WORKSPACE_ID}"

backup_resources=(
  "azurerm_backup_protected_file_share.file_share[0]"
  "azurerm_backup_container_storage_account.storage_account[0]"
  "module.backup[0].azurerm_backup_policy_file_share.file_share_policy"
  "module.backup[0].azurerm_backup_policy_vm.vm_policy"
  "module.backup[0].azurerm_recovery_services_vault.vault"
)

remove_from_state() {
  local state resource
  state="$(terraform state list)"
  for resource in "$@"; do
    if echo "${state}" | grep -qxF "${resource}"; then
      echo "Removing ${resource} from the Terraform state..."
      terraform state rm "${resource}"
    fi
  done
}

if [ "${DELETE_BACKUPS}" == "true" ]; then
  # Unregister the backup containers and delete the vault (retried because the
  # unregister can briefly return CloudInternalError), then let Terraform destroy the
  # rest of the workspace including its resource group.
  vault_url="https://management.azure.com/subscriptions/${subscription_id}/resourceGroups/${vault_resource_group}/providers/Microsoft.RecoveryServices/vaults/${vault_name}?api-version=2025-08-01"
  for _ in $(seq 1 20); do
    for bmt in "${backup_management_types[@]}"; do
      for container in $(az backup container list --vault-name "${vault_name}" --resource-group "${vault_resource_group}" \
        --backup-management-type "${bmt}" --query "[?properties.registrationStatus=='Registered'].name" --output tsv 2>/dev/null || true); do
        echo "Unregistering backup container '${container}'..."
        az backup container unregister --vault-name "${vault_name}" --resource-group "${vault_resource_group}" \
          --backup-management-type "${bmt}" --container-name "${container}" --yes --output none 2>/dev/null || true
      done
    done
    az rest --method delete --url "${vault_url}" --output none 2>/dev/null || true
    if ! az backup vault show --name "${vault_name}" --resource-group "${vault_resource_group}" --output none 2>/dev/null; then
      echo "Recovery Services Vault ${vault_name} deleted."
      break
    fi
    sleep 15
  done
  if az backup vault show --name "${vault_name}" --resource-group "${vault_resource_group}" --output none 2>/dev/null; then
    echo "Error: Recovery Services Vault ${vault_name} could not be deleted." >&2
    exit 1
  fi
  remove_from_state "${backup_resources[@]}"
  popd > /dev/null
  echo "Vault deleted. Terraform will destroy the remaining workspace resources, including the resource group."
else
  remove_from_state "${backup_resources[@]}" "azurerm_resource_group.ws"
  popd > /dev/null
  echo "Backup resources retained. Terraform will delete the other workspace resources and leave the vault and its resource group in place."
fi
