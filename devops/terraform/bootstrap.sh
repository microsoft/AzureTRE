#!/bin/bash
set -e

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
az group create --resource-group $TF_VAR_mgmt_resource_group_name --location $TF_VAR_location -o table
az storage account create --resource-group $TF_VAR_mgmt_resource_group_name \
--name $TF_VAR_mgmt_storage_account_name --location $TF_VAR_location \
--kind StorageV2 --sku Standard_LRS -o table

# Blob container
SA_KEY=$(az storage account keys list --account-name $TF_VAR_mgmt_storage_account_name --query "[0].value" -o tsv)
az storage container create --account-name $TF_VAR_mgmt_storage_account_name --name $TF_VAR_terraform_state_container_name --account-key $SA_KEY -o table
az storage share create --account-name $TF_VAR_mgmt_storage_account_name --name $TF_VAR_porter_output_container_name --account-key $SA_KEY -o table

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


# Set up Terraform
echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
terraform init -input=false -backend=true -reconfigure -upgrade

# Import the storage account & res group into state
echo -e "\n\e[34m»»» 📤 \e[96mImporting resources to state\e[0m..."
{
  terraform import azurerm_resource_group.mgmt "/subscriptions/$TF_VAR_arm_subscription_id/resourceGroups/$TF_VAR_mgmt_resource_group_name"
  terraform import azurerm_storage_account.state_storage "/subscriptions/$TF_VAR_arm_subscription_id/resourceGroups/$TF_VAR_mgmt_resource_group_name/providers/Microsoft.Storage/storageAccounts/$TF_VAR_mgmt_storage_account_name"
} || {
  echo "State already imported"
}
