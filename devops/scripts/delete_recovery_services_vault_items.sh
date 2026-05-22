#!/bin/bash

# Deletes protected backup items from Recovery Services vaults in a CI
# environment before Terraform attempts to destroy the vault.

set -o errexit
set -o pipefail
set -o nounset

function usage() {
  cat <<USAGE

    Usage: $0 --resource-group "rg-name" [--vault-name "vault-name"]

    Options:
        --resource-group   Resource group containing Recovery Services vaults.
        --vault-name       Optional Recovery Services vault name. If omitted,
                           all vaults in the resource group are cleaned.
USAGE
  exit 1
}

resource_group=""
vault_name=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --resource-group)
      shift
      resource_group="${1:-}"
      ;;
    --vault-name)
      shift
      vault_name="${1:-}"
      ;;
    *)
      echo "Unexpected argument: '$1'"
      usage
      ;;
  esac
  shift
done

if [ -z "${resource_group}" ]; then
  echo "Resource group wasn't provided"
  usage
fi

if ! az group show --name "${resource_group}" --output none 2> /dev/null; then
  echo "Resource group ${resource_group} not found - skipping Recovery Services vault cleanup"
  exit 0
fi

function wait_for_backup_jobs() {
  local vault=$1

  for attempt in {1..30}; do
    local running_jobs
    running_jobs=$(az backup job list \
      --resource-group "${resource_group}" \
      --vault-name "${vault}" \
      --status InProgress \
      --query "length(@)" \
      --output tsv)

    if [ "${running_jobs}" = "0" ]; then
      return 0
    fi

    echo "Waiting for ${running_jobs} backup job(s) to complete in ${vault} (attempt ${attempt}/30)..."
    sleep 30
  done

  echo "Timed out waiting for backup jobs to complete in ${vault}"
  return 1
}

function disable_file_share_items() {
  local vault=$1

  az backup item list \
    --resource-group "${resource_group}" \
    --vault-name "${vault}" \
    --backup-management-type AzureStorage \
    --workload-type AzureFileShare \
    --output json |
  jq -r '.[] | [.containerName, .name] | @tsv' |
  while IFS=$'\t' read -r container item; do
    if [ -z "${container}" ] || [ -z "${item}" ]; then
      continue
    fi

    echo "Deleting Azure Files backup item ${item} from ${vault}"
    az backup protection disable \
      --resource-group "${resource_group}" \
      --vault-name "${vault}" \
      --backup-management-type AzureStorage \
      --workload-type AzureFileShare \
      --container-name "${container}" \
      --item-name "${item}" \
      --delete-backup-data true \
      --yes \
      --output none
  done
}

function unregister_storage_containers() {
  local vault=$1

  az backup container list \
    --resource-group "${resource_group}" \
    --vault-name "${vault}" \
    --backup-management-type AzureStorage \
    --output json |
  jq -r '.[].name' |
  while read -r container; do
    if [ -z "${container}" ]; then
      continue
    fi

    echo "Unregistering Azure Storage backup container ${container} from ${vault}"
    az backup container unregister \
      --resource-group "${resource_group}" \
      --vault-name "${vault}" \
      --backup-management-type AzureStorage \
      --container-name "${container}" \
      --yes \
      --output none
  done
}

function disable_vm_items() {
  local vault=$1

  az backup item list \
    --resource-group "${resource_group}" \
    --vault-name "${vault}" \
    --backup-management-type AzureIaasVM \
    --workload-type VM \
    --output json |
  jq -r '.[] | [.containerName, .name] | @tsv' |
  while IFS=$'\t' read -r container item; do
    if [ -z "${container}" ] || [ -z "${item}" ]; then
      continue
    fi

    echo "Deleting Azure VM backup item ${item} from ${vault}"
    az backup protection disable \
      --resource-group "${resource_group}" \
      --vault-name "${vault}" \
      --backup-management-type AzureIaasVM \
      --workload-type VM \
      --container-name "${container}" \
      --item-name "${item}" \
      --delete-backup-data true \
      --yes \
      --output none
  done
}

function clean_vault() {
  local vault=$1

  echo "Cleaning Recovery Services vault ${vault} in ${resource_group}"

  az backup vault backup-properties set \
    --resource-group "${resource_group}" \
    --name "${vault}" \
    --soft-delete-feature-state Disable \
    --hybrid-backup-security-features Disable \
    --output none

  disable_file_share_items "${vault}"
  disable_vm_items "${vault}"
  wait_for_backup_jobs "${vault}"
  unregister_storage_containers "${vault}"
  wait_for_backup_jobs "${vault}"
}

if [ -n "${vault_name}" ]; then
  if az resource show --resource-group "${resource_group}" --resource-type "Microsoft.RecoveryServices/vaults" --name "${vault_name}" --output none 2> /dev/null; then
    clean_vault "${vault_name}"
  else
    echo "Recovery Services vault ${vault_name} not found in ${resource_group} - skipping"
  fi
else
  az backup vault list --resource-group "${resource_group}" --query "[].name" --output tsv |
  while read -r vault; do
    if [ -n "${vault}" ]; then
      clean_vault "${vault}"
    fi
  done
fi
