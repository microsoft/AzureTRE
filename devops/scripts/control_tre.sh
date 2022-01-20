#!/bin/bash
set -e

if [[ "$1" == *"start"* ]]; then
  echo -e "Starting Firewall - creating ip-config"
  az network firewall ip-config create -f "fw-$TRE_ID" -g "rg-$TRE_ID" -n "AzureFirewallIpConfiguration0" --public-ip-address "pip-fw-$TRE_ID" --vnet-name "vnet-$TRE_ID" > /dev/null

  echo -e "Starting Application Gateway"
  az network application-gateway start -g "rg-$TRE_ID" -n "agw-$TRE_ID"
fi

if [[ "$1" == *"stop"* ]]; then
  echo -e "Retrieving Firewall ip-config"
  IPCONFIG_NAME=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].name" -o tsv)

  echo -e "Deleting Firewall ip-config"
  az network firewall ip-config delete -f "fw-$TRE_ID" -n "$IPCONFIG_NAME" -g "rg-$TRE_ID"

  echo -e "Stopping Application Gateway\n"
  az network application-gateway stop -g "rg-$TRE_ID" -n "agw-$TRE_ID"
fi

# Report FW status
PUBLIC_IP=$(az network firewall ip-config list -f "fw-$TRE_ID" -g "rg-$TRE_ID" --query "[0].publicIpAddress" -o tsv)
if [ -n "$PUBLIC_IP" ]; then
  echo -e "Firewall - Running"
else
  echo -e "Firewall - Stopped"
fi

# Report AGW status
AGW_STATE=$(az network application-gateway show -g "rg-$TRE_ID" -n "agw-$TRE_ID" --query "operationalState" -o tsv)
echo -e "Application Gateway - $AGW_STATE"
