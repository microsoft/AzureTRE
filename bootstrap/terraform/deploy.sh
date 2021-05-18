#!/bin/bash
set -e

echo -e "\n\e[34m╔══════════════════════════════════╗"
echo -e "║\e[33m    Deploy Management Infra 🚀\e[34m    ║"
echo -e "║\e[32m        Terraform Script\e[34m          ║"
echo -e "╚══════════════════════════════════╝"
echo -e "\n\e[34m»»» ✅ \e[96mChecking pre-reqs\e[0m..."

# Load env vars from .env file
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

export SUB_NAME=$(az account show --query name -o tsv)
if [[ -z $SUB_NAME ]]; then
  echo -e "\n\e[31m»»» ⚠️ You are not logged in to Azure!"
  exit
fi
export TENANT_ID=$(az account show --query tenantId -o tsv)

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

echo -e "\n\e[34m»»» 📜 \e[96mTerraform plan\e[0m...\n"
terraform plan

echo -e "\n\e[34m»»» 🚀 \e[96mTerraform apply\e[0m...\n"
terraform apply -auto-approve