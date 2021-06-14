#!/bin/bash
set -e

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
az group create --resource-group $MGMT_RESOURCE_GROUP_NAME --location $LOCATION -o table
az storage account create --resource-group $MGMT_RESOURCE_GROUP_NAME \
--name $MGMT_STORAGE_ACCOUNT_NAME --location $LOCATION \
--kind StorageV2 --sku Standard_LRS -o table

# Blob container
SA_KEY=$(az storage account keys list --account-name $MGMT_STORAGE_ACCOUNT_NAME --query "[0].value" -o tsv)
az storage container create --account-name $MGMT_STORAGE_ACCOUNT_NAME --name $TERRAFORM_STATE_CONTAINER_NAME --account-key $SA_KEY -o table

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
terraform init -input=false -backend=true -reconfigure 

# Import the storage account & res group into state
echo -e "\n\e[34m»»» 📤 \e[96mImporting resources to state\e[0m..."
{
  terraform import azurerm_resource_group.mgmt "/subscriptions/$SUB_ID/resourceGroups/$MGMT_RESOURCE_GROUP_NAME"
  terraform import azurerm_storage_account.state_storage "/subscriptions/$SUB_ID/resourceGroups/$MGMT_RESOURCE_GROUP_NAME/providers/Microsoft.Storage/storageAccounts/$MGMT_STORAGE_ACCOUNT_NAME"
} || {
  echo "State already imported"
}
