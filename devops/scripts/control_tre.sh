#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

if [[ -z ${TRE_ID:-} ]]; then
    echo "TRE_ID environment variable must be set."
    exit 1
fi

# if the resource group doesn't exist, no need to continue this script.
# most likely this is an automated execution before calling make tre-deploy.
if [[ $(az group list --query "[?name=='rg-${TRE_ID}'] | length(@)") == 0 ]]; then
  echo "TRE resource group doesn't exits. Exiting..."
  exit 0
fi

az config set extension.use_dynamic_install=yes_without_prompt

if [[ "$1" == *"start"* ]]; then
  if [[ $(az network firewall list --query "[?resourceGroup=='rg-${TRE_ID}'&&name=='fw-${TRE_ID}'] | length(@)") != 0 ]]; then
    CURRENT_PUBLIC_IP=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].publicIpAddress" -o tsv)
    if [ -z "$CURRENT_PUBLIC_IP" ]; then
      echo "Starting Firewall - creating ip-config"
      az network firewall ip-config create -f "fw-$TRE_ID" -g "rg-$TRE_ID" -n "fw-ip-configuration" --public-ip-address "pip-fw-$TRE_ID" --vnet-name "vnet-$TRE_ID" > /dev/null
    else
      echo "Firewall ip-config already exists"
    fi
  fi

  if [[ $(az network application-gateway list --query "[?resourceGroup=='rg-${TRE_ID}'&&name=='agw-${TRE_ID}'&&operationalState=='Stopped'] | length(@)") != 0 ]]; then
    echo "Starting Application Gateway"
    az network application-gateway start -g "rg-$TRE_ID" -n "agw-$TRE_ID"
  else
    echo "Application Gateway already running"
  fi
elif [[ "$1" == *"stop"* ]]; then
  if [[ $(az network firewall list --query "[?resourceGroup=='rg-${TRE_ID}'&&name=='fw-${TRE_ID}'] | length(@)") != 0 ]]; then
    IPCONFIG_NAME=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].name" -o tsv)

    if [ -n "$IPCONFIG_NAME" ]; then
      echo "Deleting Firewall ip-config: $IPCONFIG_NAME"
      az network firewall ip-config delete -f "fw-$TRE_ID" -n "$IPCONFIG_NAME" -g "rg-$TRE_ID"
    else
      echo "No Firewall ip-config found"
    fi
  fi

  if [[ $(az network application-gateway list --query "[?resourceGroup=='rg-${TRE_ID}'&&name=='agw-${TRE_ID}'&&operationalState=='Running'] | length(@)") != 0 ]]; then
    az network application-gateway stop -g "rg-$TRE_ID" -n "agw-$TRE_ID"
  else
    echo "Application Gateway already stopped"
  fi
fi

# Report final FW status
PUBLIC_IP=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].publicIpAddress" -o tsv)
if [ -n "$PUBLIC_IP" ]; then
  FW_STATE="Running"
else
  FW_STATE="Stopped"
fi

# Report final AGW status
AGW_STATE=$(az network application-gateway list --query "[?resourceGroup=='rg-${TRE_ID}'&&name=='agw-${TRE_ID}'].operationalState | [0]" -o tsv)

echo -e "\n\e[34m»»» 🔨 \e[96mTRE Status for $TRE_ID\e[0m"
echo -e "\e[34m»»»   • \e[96mFirewall:              \e[33m$FW_STATE\e[0m"
echo -e "\e[34m»»»   • \e[96mApplication Gateway:   \e[33m$AGW_STATE\e[0m\n"
