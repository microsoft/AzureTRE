#!/bin/bash
set -e

echo -e "\n\e[34m╔══════════════════════════════════╗"
echo -e "║\e[33m    Deploy Azure TRE 🚀\e[34m    ║"
echo -e "║\e[32m        Terraform Script\e[34m          ║"
echo -e "╚══════════════════════════════════╝"
echo -e "\n\e[34m»»» ✅ \e[96mChecking pre-reqs\e[0m..."

# Load state env vars from .env file
PATH_STATE_ENV="../../../bootstrap/terraform/.env"
if [ ! -f $PATH_STATE_ENV ]; then
  echo -e "\e[31m»»» 💥 Unable to find bootstrap .env file, please create file and try again!"
  exit
else
  echo -e "\n\e[34m»»» 🧩 \e[96mLoading bootstrap environmental variables\e[0m..."
  export $(egrep -v '^#' $PATH_STATE_ENV | xargs)
fi

# Load env vars from .env file
if [ ! -f ".env" ]; then
  echo -e "\e[31m»»» 💥 Unable to find core .env file, please create file and try again!"
  exit
else
  echo -e "\n\e[34m»»» 🧩 \e[96mLoading core environmental variables\e[0m..."
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

export SUB_NAME=$(az account show --query name -o tsv)
if [[ -z $SUB_NAME ]]; then
  echo -e "\n\e[31m»»» ⚠️ You are not logged in to Azure!"
  exit
fi
export TENANT_ID=$(az account show --query tenantId -o tsv)

echo -e "\e[34m»»» 🔨 \e[96mAzure details from logged on user \e[0m"
echo -e "\e[34m»»»   • \e[96mSubscription: \e[33m$SUB_NAME\e[0m"
echo -e "\e[34m»»»   • \e[96mTenant:       \e[33m$TENANT_ID\e[0m\n"

cat > bootstrap_backend.tf <<TRE_BACKEND
terraform {
  backend "azurerm" {
    resource_group_name  = "$TF_VAR_mgmt_res_group"
    storage_account_name = "$TF_VAR_state_storage"
    container_name       = "$TF_VAR_state_container"
    key                  = "$TF_VAR_resource_name_prefix$TF_VAR_environment"
  }
}
TRE_BACKEND

ACR_NAME="${TF_VAR_resource_name_prefix}acr"
export TF_VAR_docker_registry_server="${TF_VAR_resource_name_prefix}acr.azurecr.io"
export TF_VAR_docker_registry_username="${TF_VAR_resource_name_prefix}acr"
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_resource_name_prefix}acr --query passwords[0].value | sed 's/"//g')
export TF_VAR_management_api_image_tag=$TF_VAR_resource_name_prefix

echo -e "\n\e[34m»»» ✨ \e[96mTerraform init\e[0m..."
terraform init -input=false -backend=true -reconfigure

echo -e "\n\e[34m»»» 🚀 \e[96mTerraform destroy\e[0m...\n"
terraform destroy