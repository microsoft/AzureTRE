#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
# shellcheck disable=SC2154
az group create --resource-group "$TF_VAR_mgmt_resource_group_name" --location "$LOCATION" -o table
# shellcheck disable=SC2154
az storage account create --resource-group "$TF_VAR_mgmt_resource_group_name" \
  --name "$TF_VAR_mgmt_storage_account_name" --location "$LOCATION" \
  --allow-blob-public-access false \
  --kind StorageV2 --sku Standard_LRS -o table

# Grant user blob data contributor permissions
echo -e "\n\e[34m»»» 🔑 \e[96mGranting Storage Blob Data Contributor role to the current user\e[0m..."
if [ -n "${ARM_CLIENT_ID:-}" ]; then
    USER_OBJECT_ID=$(az ad sp show --id "$ARM_CLIENT_ID" --query id --output tsv)
else
    USER_OBJECT_ID=$(az ad signed-in-user show --query id --output tsv)
fi
az role assignment create --assignee "$USER_OBJECT_ID" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"

# Function to check if the role assignment exists
check_role_assignment() {
  az role assignment list --assignee "$USER_OBJECT_ID" --role "Storage Blob Data Contributor" --scope "/subscriptions/$ARM_SUBSCRIPTION_ID/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name" --query "[].id" --output tsv
}

# Wait for the role assignment to be applied
echo -e "\n\e[34m»»» ⏳ \e[96mWaiting for role assignment to be applied\e[0m..."
while [ -z "$(check_role_assignment)" ]; do
  echo "Waiting for role assignment..."
  sleep 10
done
echo "Role assignment applied."

# Blob container
# shellcheck disable=SC2154
az storage container create --account-name "$TF_VAR_mgmt_storage_account_name" --name "$TF_VAR_terraform_state_container_name" --auth-mode login -o table

# logs container
az storage container create --account-name "$TF_VAR_mgmt_storage_account_name" --name "tflogs" --auth-mode login -o table

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
