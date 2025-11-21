#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

retry_with_backoff() {
  local func="$1"
  local sleep_time=10
  local max_sleep=180

  while [ "$sleep_time" -lt "$max_sleep" ]; do
    if "$func"; then
      return 0
    fi
    sleep "$sleep_time"
    sleep_time=$((sleep_time * 2))
  done
  return 1
}

init_terraform() {
  terraform_output=$(terraform init -input=false -backend=true -reconfigure 2>&1)
  if echo "$terraform_output" | grep -q "AuthorizationPermissionMismatch\|403\|Failed to get existing workspaces"; then
    return 1
  elif echo "$terraform_output" | grep -q "Terraform has been successfully initialized"; then
    return 0
  fi

  echo "Apply Retry mechanism on: ERROR- Unexpected output from terraform init: $terraform_output"
  return 1
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


echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
# shellcheck disable=SC2154
cat > bootstrap_backend.tf <<BOOTSTRAP_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_resource_group_name"
    storage_account_name = "$TF_VAR_mgmt_storage_account_name"
    container_name       = "$TF_VAR_terraform_state_container_name"
    key                  = "bootstrap.tfstate"
    use_azuread_auth     = true
    use_oidc             = true
  }
}
BOOTSTRAP_BACKEND

# shellcheck disable=SC2154
if ! retry_with_backoff init_terraform; then
  echo "ERROR: Timeout waiting for Terraform backend role assignments."
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
