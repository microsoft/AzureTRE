#!/bin/bash
set -e

echo -e "\n\e[34m╔══════════════════════════════════╗"
echo -e "║\e[33m    Buidl andPublish Docker Images 🚀\e[34m    ║"
echo -e "║\e[32m        \e[34m          ║"
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

docker version > /dev/null 2>&1
if [ $? -ne 0 ]; then
  echo -e "\e[31m»»» ⚠️ Docker is not installed! 😥 Please go to hhttps://docs.docker.com/engine/install/ to set it up"
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

echo -e "\n\e[34m»»» 📜 \e[96mACR login\e[0m...\n"
ACR_NAME="${TF_VAR_resource_name_prefix}acr"
az acr login --name ${TF_VAR_resource_name_prefix}acr 

REPOSITORY_NAME="$ACR_NAME.azurecr.io/microsoft/azuretre/management-api"
TAG=$TF_VAR_image_tag

echo -e "\n\e[34m»»» 🚀 \e[96mBuild images\e[0m...\n"
docker build -t $REPOSITORY_NAME:$TAG ../../core/api/  

echo -e "\n\e[34m»»» 🚀 \e[96mPush images\e[0m...\n"
docker push $REPOSITORY_NAME:$TAG