#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

if [[ -z ${TRE_ID:-} ]]; then
    echo "TRE_ID environment variable must be set."
    exit 1
fi

core_rg_name="rg-${TRE_ID}"
fw_name="fw-${TRE_ID}"
agw_name="agw-$TRE_ID"
fw_pip_name="pip-${fw_name}"
vnet_name="vnet-${TRE_ID}"

# if the resource group doesn't exist, no need to continue this script.
# most likely this is an automated execution before calling make tre-deploy.
if [[ $(az group list --output json --query "[?name=='${core_rg_name}'] | length(@)") == 0 ]]; then
  echo "TRE resource group doesn't exist. Exiting..."
  exit 0
fi

az config set extension.use_dynamic_install=yes_without_prompt
az --version

if [[ "$1" == *"start"* ]]; then
  if [[ $(az network firewall list --output json --query "[?resourceGroup=='${core_rg_name}'&&name=='${fw_name}'] | length(@)") != 0 ]]; then
    CURRENT_PUBLIC_IP=$(az network firewall ip-config list -f "${fw_name}" -g "${core_rg_name}" --query "[0].publicIpAddress" -o tsv)
    if [ -z "$CURRENT_PUBLIC_IP" ]; then
      FW_SKU_TIER=$(az network firewall show --n "${fw_name}" -g "${core_rg_name}" --query "sku.tier" -o tsv)
      if [ "$FW_SKU_TIER" == "Basic" ]; then
        echo "Starting Firewall (Basic SKU) - creating ip-config and management-ip-config"
        az network firewall ip-config create -f "${fw_name}" -g "${core_rg_name}" -n "fw-ip-configuration" --public-ip-address "${fw_pip_name}" --vnet-name "${vnet_name}" --m-name "fw-management-ip-configuration" --m-public-ip-address "pip-fw-management-$TRE_ID" --m-vnet-name "${vnet_name}"> /dev/null &
      else
        echo "Starting Firewall - creating ip-config"
        az network firewall ip-config create -f "${fw_name}" -g "${core_rg_name}" -n "fw-ip-configuration" --public-ip-address "${fw_pip_name}" --vnet-name "${vnet_name}" > /dev/null &
      fi
    else
      echo "Firewall ip-config already exists"
    fi
  fi

  if [[ $(az network application-gateway list --output json --query "[?resourceGroup=='${core_rg_name}'&&name=='${agw_name}'&&operationalState=='Stopped'] | length(@)") != 0 ]]; then
    echo "Starting Application Gateway"
    az network application-gateway start -g "${core_rg_name}" -n "${agw_name}" &
  else
    echo "Application Gateway already running"
  fi

  az mysql flexible-server list --resource-group "${core_rg_name}" --query "[?userVisibleState=='Stopped'].name" -o tsv |
  while read -r mysql_name; do
    echo "Starting MySQL ${mysql_name}"
    az mysql flexible-server start --resource-group "${core_rg_name}" --name "${mysql_name}" &
  done

  az vmss list --resource-group "${core_rg_name}" --query "[].name" -o tsv |
  while read -r vmss_name; do
    if [[ "$(az vmss list-instances --resource-group "${core_rg_name}" --name "${vmss_name}" --expand instanceView --output json | \
      jq 'select(.[].instanceView.statuses[].code=="PowerState/deallocated") | length')" -gt 0 ]]; then
      echo "Starting VMSS ${vmss_name}"
      az vmss start --resource-group "${core_rg_name}" --name "${vmss_name}" &
    fi
  done

  az vm list -d --resource-group "${core_rg_name}" --query "[?powerState!='VM running'].name" -o tsv |
  while read -r vm_name; do
    echo "Starting VM ${vm_name}"
    az vm start --resource-group "${core_rg_name}" --name "${vm_name}" &
  done

  # We don't start workspace VMs despite maybe stopping them because we don't know if they need to be on.

elif [[ "$1" == *"stop"* ]]; then
  if [[ $(az network firewall list --output json --query "[?resourceGroup=='${core_rg_name}'&&name=='${fw_name}'] | length(@)") != 0 ]]; then
    IPCONFIG_NAME=$(az network firewall ip-config list -f "${fw_name}" -g "${core_rg_name}" --query "[0].name" -o tsv)

    if [ -n "$IPCONFIG_NAME" ]; then
      echo "Deleting Firewall ip-config"
      az network firewall update --name "${fw_name}" --resource-group "${core_rg_name}" --remove ipConfigurations --remove managementIpConfiguration &
    else
      echo "No Firewall ip-config found"
    fi
  fi

  if [[ $(az network application-gateway list --output json --query "[?resourceGroup=='${core_rg_name}'&&name=='${agw_name}'&&operationalState=='Running'] | length(@)") != 0 ]]; then
    echo "Stopping Application Gateway"
    az network application-gateway stop -g "${core_rg_name}" -n "${agw_name}" &
  else
    echo "Application Gateway already stopped"
  fi

  az mysql flexible-server list --resource-group "${core_rg_name}" --query "[?userVisibleState=='Ready'].name" -o tsv |
  while read -r mysql_name; do
    echo "Stopping MySQL ${mysql_name}"
    az mysql flexible-server stop --resource-group "${core_rg_name}" --name "${mysql_name}" &
  done

  az vmss list --resource-group "${core_rg_name}" --query "[].name" -o tsv |
  while read -r vmss_name; do
    if [[ "$(az vmss list-instances --resource-group "${core_rg_name}" --name "${vmss_name}" --expand instanceView --output json | \
      jq 'select(.[].instanceView.statuses[].code=="PowerState/running") | length')" -gt 0 ]]; then
      echo "Deallocating VMSS ${vmss_name}"
      az vmss deallocate --resource-group "${core_rg_name}" --name "${vmss_name}" &
    fi
  done

  az vm list -d --resource-group "${core_rg_name}" --query "[?powerState=='VM running'].name" -o tsv |
  while read -r vm_name; do
    echo "Deallocating VM ${vm_name}"
    az vm deallocate --resource-group "${core_rg_name}" --name "${vm_name}" &
  done

  # deallocating all VMs in workspaces
  # RG is in uppercase here (which is odd). Checking both cases for future compatability.
  az vm list -d --query "[?(starts_with(resourceGroup,'${core_rg_name}-ws') || starts_with(resourceGroup,'${core_rg_name^^}-WS')) && powerState=='VM running'][name, resourceGroup]" -o tsv |
  while read -r vm_name rg_name; do
    echo "Deallocating VM ${vm_name} in ${rg_name}"
    az vm deallocate --resource-group "${rg_name}" --name "${vm_name}" &
  done
fi

# for some reason the vm/vmss commands aren't considered as 'jobs', but this will still work in most cases
# since firewall/appgw will take much longer to complete their change.
echo "Waiting for all jobs to finish..."
jobs
wait

# Report final FW status
FW_STATE="Stopped"
if [[ $(az network firewall list --output json --query "[?resourceGroup=='${core_rg_name}'&&name=='${fw_name}'] | length(@)") != 0 ]]; then
  PUBLIC_IP=$(az network firewall ip-config list -f "${fw_name}" -g "${core_rg_name}" --query "[0].publicIpAddress" -o tsv)
  if [ -n "$PUBLIC_IP" ]; then
    FW_STATE="Running"
  fi
fi

# Report final AGW status
AGW_STATE=$(az network application-gateway list --query "[?resourceGroup=='${core_rg_name}'&&name=='${agw_name}'].operationalState | [0]" -o tsv)

echo -e "\n\e[34m»»» 🔨 \e[96mTRE Status for $TRE_ID\e[0m"
echo -e "\e[34m»»»   • \e[96mFirewall:              \e[33m$FW_STATE\e[0m"
echo -e "\e[34m»»»   • \e[96mApplication Gateway:   \e[33m$AGW_STATE\e[0m\n"
