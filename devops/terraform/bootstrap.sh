#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

retry_with_backoff() {
  local func="$1"
  local sleep_time
  local status

  for sleep_time in 10 20 40 80 160; do
    if "$func"; then
      return 0
    else
      status=$?
    fi
    # A status of 1 is retryable. Other failures must retain their diagnostics.
    if [ "$status" -ne 1 ]; then
      return "$status"
    fi
    echo "Retrying ${func} in ${sleep_time} seconds..." >&2
    sleep "$sleep_time"
  done
  "$func"
}

is_storage_permission_error() {
  # Azure CLI can replace storage error codes with these messages before printing them.
  grep -Eq 'AuthorizationPermissionMismatch|AuthorizationFailure|(^|[^[:alnum:]])403([^[:alnum:]]|$)' <<< "$1" \
    || grep -Fq \
      -e 'You do not have the required permissions needed to perform this operation.' \
      -e 'The request may be blocked by network rules of storage account.' <<< "$1"
}

check_blob_access() {
  local output
  # Container operations can succeed through Owner before blob data access is ready.
  # Check the data permission Terraform needs, even when the state container is empty.
  # shellcheck disable=SC2154
  if output=$(az storage blob list \
    --account-name "$TF_VAR_mgmt_storage_account_name" \
    --container-name "$TF_VAR_terraform_state_container_name" \
    --prefix bootstrap.tfstate --num-results 1 \
    --auth-mode login --only-show-errors --output none 2>&1); then
    return 0
  fi

  printf '%s\n' "$output" >&2
  if is_storage_permission_error "$output"; then
    return 1
  fi
  return 2
}

init_terraform() {
  local terraform_output
  local status
  if terraform_output=$(terraform init -input=false -backend=true -reconfigure -no-color 2>&1); then
    printf '%s\n' "$terraform_output"
    return 0
  else
    status=$?
  fi

  printf 'ERROR: terraform init failed (exit %s).\n%s\n' "$status" "$terraform_output" >&2
  # An unlock failure can also contain a 403. Never hide it or retry it as role propagation.
  if grep -Eiq 'Error (acquiring|releasing|locking|unlocking)|failed to (lock|unlock)|state blob is already locked|Lock Info:|Lock ID:' <<< "$terraform_output"; then
    echo "ERROR: Check the reported lock owner before attempting state recovery. No lock has been released by bootstrap." >&2
    return 2
  fi
  # Retry only workspace-listing permission failures, not unknown state errors.
  if grep -Fq 'Failed to get existing workspaces' <<< "$terraform_output" \
    && is_storage_permission_error "$terraform_output"; then
    return 1
  fi
  return 2
}

check_role_assignments() {
  local roles
  # shellcheck disable=SC2154
  roles=$(az role assignment list \
    --assignee "$USER_OBJECT_ID" \
    --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name" \
    --query "[?roleDefinitionName=='Storage Blob Data Contributor'].roleDefinitionName" --output tsv)

  if [[ $roles == *"Storage Blob Data Contributor"* ]]; then
    return 0
  fi
  return 1
}

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
# shellcheck disable=SC2154
az group create --resource-group "$TF_VAR_mgmt_resource_group_name" --location "$LOCATION" -o table

# shellcheck disable=SC2154
if ! az storage account show --resource-group "$TF_VAR_mgmt_resource_group_name" --name "$TF_VAR_mgmt_storage_account_name" --query "name" -o none 2>/dev/null; then
  # only run `az storage account create` if doesn't exist (to prevent error from occuring if storage account was originally created without infrastructure encryption enabled)

  # Set default encryption types based on enable_cmk
  encryption_type=$([ "${TF_VAR_enable_cmk_encryption:-false}" = true ] && echo "Account" || echo "Service")

  # shellcheck disable=SC2154
  az storage account create --resource-group "$TF_VAR_mgmt_resource_group_name" \
    --name "$TF_VAR_mgmt_storage_account_name" --location "$LOCATION" \
    --allow-blob-public-access false --min-tls-version TLS1_2 \
    --kind StorageV2 --sku Standard_LRS -o table \
    --encryption-key-type-for-queue "$encryption_type" \
    --encryption-key-type-for-table "$encryption_type" \
    --require-infrastructure-encryption true
else
  echo "Storage account already exists..."
  az storage account show --resource-group "$TF_VAR_mgmt_resource_group_name" --name "$TF_VAR_mgmt_storage_account_name" --output table
fi

# shellcheck disable=SC1091
source ../scripts/storage_enable_public_access.sh \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}"

# Grant user blob data contributor permissions
echo -e "\n\e[34m»»» 🔑 \e[96mGranting Storage Blob Data Contributor role to the current user\e[0m..."
if [ -n "${ARM_CLIENT_ID:-}" ]; then
    USER_OBJECT_ID=$(az ad sp show --id "$ARM_CLIENT_ID" --query id --output tsv)
else
    USER_OBJECT_ID=$(az ad signed-in-user show --query id --output tsv)
fi

# shellcheck disable=SC2154
az role assignment create --assignee "$USER_OBJECT_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"

if ! retry_with_backoff check_role_assignments; then
  echo "ERROR: Timeout waiting for az role assignments."
  exit 1
fi


echo -e "\n\e[34m»»» 📦 \e[96mCreating storage containers\e[0m..."
# shellcheck disable=SC2154
containers=("$TF_VAR_terraform_state_container_name" "tflogs")
max_retries=8

for container in "${containers[@]}"; do
  for ((i=1; i<=max_retries; i++)); do
    if az storage container create --account-name "$TF_VAR_mgmt_storage_account_name" --name "$container" --auth-mode login -o table; then
      echo "Container '$container' created successfully."
      break
    else
      sleep 10
    fi
    if [ $i -eq $max_retries ]; then
      echo "ERROR: Failed to create container '$container' after $max_retries attempts."
      exit 1
    fi
  done
done

echo "Checking blob data access before initialising Terraform..."
if ! retry_with_backoff check_blob_access; then
  echo "ERROR: Bootstrap blob access check failed. Terraform has not been started." >&2
  exit 1
fi

echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
# shellcheck disable=SC2154
cat > bootstrap_backend.tf <<BOOTSTRAP_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_resource_group_name"
    storage_account_name = "$TF_VAR_mgmt_storage_account_name"
    container_name       = "$TF_VAR_terraform_state_container_name"
    key                  = "bootstrap.tfstate"
  }
}
BOOTSTRAP_BACKEND

# shellcheck disable=SC2154
if ! retry_with_backoff init_terraform; then
  echo "ERROR: Terraform backend initialisation failed. See the error above." >&2
  exit 1
fi
echo -e "\n\e[34m»»» 📤 \e[96mImporting resources to state\e[0m..."
if ! terraform state show azurerm_resource_group.mgmt > /dev/null; then
  echo  "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name"
  terraform import azurerm_resource_group.mgmt "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name"
fi

if ! terraform state show azurerm_storage_account.state_storage > /dev/null; then
  terraform import azurerm_storage_account.state_storage "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"
fi
echo "State imported"
set +o nounset
