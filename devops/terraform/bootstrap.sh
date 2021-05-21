#!/bin/bash
set -e

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
az group create --resource-group $TF_VAR_mgmt_res_group --location $TF_VAR_location -o table
az storage account create --resource-group $TF_VAR_mgmt_res_group \
--name $TF_VAR_state_storage --location $TF_VAR_location \
--kind StorageV2 --sku Standard_LRS -o table

# Blob container
SA_KEY=$(az storage account keys list --account-name $TF_VAR_state_storage --query "[0].value" -o tsv)
az storage container create --account-name $TF_VAR_state_storage --name $TF_VAR_state_container --account-key $SA_KEY -o table

cat > bootstrap_backend.tf <<BOOTSTRAP_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_res_group"
    storage_account_name = "$TF_VAR_state_storage"
    container_name       = "$TF_VAR_state_container"
    key                  = "bootstrap.tfstate"
  }
}
BOOTSTRAP_BACKEND

# Set up Terraform
echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
terraform init -input=false -backend=true -reconfigure 

# Import the storage account & res group into state
echo -e "\n\e[34m»»» 📤 \e[96mImporting resources to state\e[0m..."
terraform import azurerm_resource_group.mgmt "/subscriptions/$SUB_ID/resourceGroups/$TF_VAR_mgmt_res_group"
terraform import azurerm_storage_account.state_storage "/subscriptions/$SUB_ID/resourceGroups/$TF_VAR_mgmt_res_group/providers/Microsoft.Storage/storageAccounts/$TF_VAR_state_storage"