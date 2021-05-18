#!/bin/bash

echo -e "\n\e[34m╔══════════════════════════════════════╗"
echo -e "║\e[33m   Terraform Backend Bootstrap! 🥾\e[34m    ║"
echo -e "║\e[32m        One time setup script \e[34m        ║"
echo -e "╚══════════════════════════════════════╝"

echo -e "\n\e[34m»»» ✅ \e[96mChecking pre-reqs\e[0m..."

# Load env variables from .env file
if [ ! -f ".env" ]; then
  echo -e "\e[31m»»» 💥 Unable to find .env file, please create file and try again!"
  exit
else
  echo -e "\n\e[34m»»» 🧩 \e[96mLoading environmental variables\e[0m..."
  export $(egrep -v '^#' ".env" | xargs)
fi

az > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo -e "\e[31m»»» ⚠️ Azure CLI is not installed! 😥 Please go to http://aka.ms/cli to set it up"
  exit
fi

terraform version > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo -e "\e[31m»»» ⚠️ Terraform is not installed! 😥 Please go to https://www.terraform.io/downloads.html to set it up"
  exit
fi

SUB_NAME=$(az account show --query name -o tsv)
SUB_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
if [ -z $SUB_NAME ]; then
  echo -e "\n\e[31m»»» ⚠️ You are not logged in to Azure!"
  exit
fi

echo -e "\e[34m»»» 🔨 \e[96mAzure details from logged on user \e[0m"
echo -e "\e[34m»»»   • \e[96mSubscription: \e[33m$SUB_NAME\e[0m"
echo -e "\e[34m»»»   • \e[96mTenant:       \e[33m$TENANT_ID\e[0m\n"

read -p " - Are these details correct, do you want to continue (y/n)? " answer
case ${answer:0:1} in
    y|Y )
    ;;
    * )
        echo -e "\e[31m»»» 😲 Deployment canceled\e[0m\n"
        exit
    ;;
esac

# Baseline Azure resources
echo -e "\n\e[34m»»» 🤖 \e[96mCreating resource group and storage account\e[0m..."
az group create --resource-group $TF_VAR_mgmt_res_group --location $TF_VAR_region -o table
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