#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

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
source ../scripts/mgmtstorage_enable_public_access.sh

# Grant user blob data contributor permissions
echo -e "\n\e[34m»»» 🔑 \e[96mGranting Storage Blob Data Contributor role to the current user\e[0m..."
if [ -n "${ARM_CLIENT_ID:-}" ]; then
    USER_OBJECT_ID=$(az ad sp show --id "$ARM_CLIENT_ID" --query id --output tsv)
else
    USER_OBJECT_ID=$(az ad signed-in-user show --query id --output tsv)
fi

az role assignment create --assignee "$USER_OBJECT_ID" \
  --role "Storage Account Contributor" \
  --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"

az role assignment create --assignee "$USER_OBJECT_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"

check_role_assignments() {
  if az storage container list \
    --account-name "$TF_VAR_mgmt_storage_account_name" \
    --auth-mode login \
    --output none 2>/dev/null; then
    echo "has_access"
  fi
}

# Wait for the role assignment to be applied
sleep_time=10
while [ "$sleep_time" -lt 180 ]; do
  sleep "$sleep_time"
  sleep_time=$((sleep_time * 2))
  if [ -n "$(check_role_assignments)" ]; then
    break
  fi
done

if [ -z "$(check_role_assignments)" ]; then
  echo "ERROR: Timeout waiting for role assignments."
  exit 1
fi

# Blob container
# shellcheck disable=SC2154

echo -e "\n\e[34m»»» 📦 \e[96mCreating storage containers\e[0m..."
# List of containers to create
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


# Set up Terraform
echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
terraform init -input=false -backend=true -reconfigure

# Import the storage account & res group into state
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
