#!/bin/bash
set -e

echo -e "\n\e[34m╔══════════════════════════════════════╗"
echo -e "║          \e[33mAzure TRE Makefile\e[34m          ║"
echo -e "╚══════════════════════════════════════╝"

echo -e "\n\e[34m»»» ✅ \e[96mChecking pre-reqs\e[0m..."

echo -e "\n\e[96mChecking for Azure CLI\e[0m..."
if [ $? -ne 0 ]; then
  echo -e "\e[31m»»» ⚠️ Azure CLI is not installed! 😥 Please go to http://aka.ms/cli to set it up"
  exit
fi

if [[ "$1" != *"nodocker"* ]]; then
  echo -e "\n\e[96mChecking for Docker\e[0m..."
  sudo docker version > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo -e "\e[31m»»» ⚠️ Docker is not installed! 😥 Please go to https://docs.docker.com/engine/install/ to set it up"
    exit
  fi
fi

if  [[ "$1" == *"certbot"* ]]; then
  echo -e "\n\e[96mChecking for Certbot\e[0m..."
  /opt/certbot/bin/certbot --version > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo -e "\e[31m»»» ⚠️ Certbot is not installed! 😥 Please go to https://certbot.eff.org/lets-encrypt/pip-other to set it up"
    exit
  fi
fi

if [[ "$1" == *"porter"* ]]; then
  echo -e "\n\e[96mChecking for porter\e[0m..."
  porter --version > /dev/null 2>&1
  if [ $? -ne 0 ]; then
    echo -e "\e[31m»»» ⚠️ Porter is not installed! 😥 Please go to https://porter.sh/install/ to set it up"
    exit
  fi
fi

export SUB_NAME=$(az account show --query name -o tsv)
export SUB_ID=$(az account show --query id -o tsv)
export TENANT_ID=$(az account show --query tenantId -o tsv)
if [ -z "$SUB_NAME" ]; then
  echo -e "\n\e[31m»»» ⚠️ You are not logged in to Azure!"
  exit
fi

echo -e "\e[34m»»» 🔨 \e[96mAzure details from logged on user \e[0m"
echo -e "\e[34m»»»   • \e[96mSubscription: \e[33m$SUB_NAME\e[0m"
echo -e "\e[34m»»»   • \e[96mTenant:       \e[33m$TENANT_ID\e[0m\n"