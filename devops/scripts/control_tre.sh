#!/bin/bash
set -e

if [[ "$1" == *"start"* ]]; then
  CURRENT_PUBLIC_IP=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].publicIpAddress" -o tsv)
  if [ -z "$CURRENT_PUBLIC_IP" ]; then
    echo -e "Starting Firewall - creating ip-config"
    az network firewall ip-config create -f "fw-$TRE_ID" -g "rg-$TRE_ID" -n "fw-ip-configuration" --public-ip-address "pip-fw-$TRE_ID" --vnet-name "vnet-$TRE_ID" > /dev/null
  else
    echo -e "Firewall ip-config already exists"
  fi

  CURRENT_AGW_STATE=$(az network application-gateway show -g "rg-$TRE_ID" -n "agw-$TRE_ID" --query "operationalState" -o tsv)
  if [[ "$CURRENT_AGW_STATE" != "Running" ]]; then
    echo -e "Starting Application Gateway\n"
    az network application-gateway start -g "rg-$TRE_ID" -n "agw-$TRE_ID"
  else
    echo -e "Application Gateway already running"
  fi
elif [[ "$1" == *"stop"* ]]; then
  IPCONFIG_NAME=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].name" -o tsv)

  if [ -n "$IPCONFIG_NAME" ]; then
    echo -e "Deleting Firewall ip-config: $IPCONFIG_NAME"
    az network firewall ip-config delete -f "fw-$TRE_ID" -n "$IPCONFIG_NAME" -g "rg-$TRE_ID"
  else
    echo -e "No Firewall ip-config found"
  fi

  CURRENT_AGW_STATE=$(az network application-gateway show -g "rg-$TRE_ID" -n "agw-$TRE_ID" --query "operationalState" -o tsv)
  if [[ "$CURRENT_AGW_STATE" != "Stopped" ]]; then
    az network application-gateway stop -g "rg-$TRE_ID" -n "agw-$TRE_ID"
  else
    echo -e "Application Gateway already stopped"
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
AGW_STATE=$(az network application-gateway show -g "rg-$TRE_ID" -n "agw-$TRE_ID" --query "operationalState" -o tsv)

echo -e "\n\e[34m»»» 🔨 \e[96mTRE Status for $TRE_ID\e[0m"
echo -e "\e[34m»»»   • \e[96mFirewall:              \e[33m$FW_STATE\e[0m"
echo -e "\e[34m»»»   • \e[96mApplication Gateway:   \e[33m$AGW_STATE\e[0m\n"
