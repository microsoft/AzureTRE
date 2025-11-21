#!/bin/bash

#
# Temporarily set Key Vault to public access for deployment, and restore to private on script exit
#
# Note:  Ensure you "source" this script, or else the EXIT trap won't fire at the right time
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"


function kv_add_network_exception() {

  # set up variables
  #
  local KV_NAME
  KV_NAME=$(get_kv_name)

  # ensure kv exists
  #
  if ! does_kv_exist "$KV_NAME"; then
    return 0   # don't cause outer sourced script to fail
  fi

  # If we have allowed access from a specific subnet, enable public access with deny default and add the network rule
  # This logic is needed to avoid error, if there is a change in subnet after the initial deployment
  if [[ -n ${PRIVATE_AGENT_SUBNET_ID:-} ]]; then
    echo -e "\nEnabling public access and adding network rule to allow subnet access for key vault $KV_NAME..."
    az keyvault update --name "$KV_NAME" --public-network-access Enabled --default-action Deny --output none
    az keyvault network-rule add --name "$KV_NAME" --subnet "$PRIVATE_AGENT_SUBNET_ID" --output none
  else
    echo -e "\nEnabling public access for key vault $KV_NAME for deployment..."
    az keyvault update --name "$KV_NAME" --public-network-access Enabled --default-action Allow --output none
  fi

  local ATTEMPT=1
  local MAX_ATTEMPTS=10

  while true; do

    if KV_OUTPUT=$(az keyvault secret list --vault-name "$KV_NAME" --query '[].name' --output tsv 2>&1); then
      echo -e " Keyvault $KV_NAME is now accessible\n"
      break
    fi

    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
      echo -e "Could not set public access for $KV_NAME"
      echo -e "Unable to access keyvault $KV_NAME after $ATTEMPT/$MAX_ATTEMPTS.\n"
      echo -e "$KV_OUTPUT\n"

      exit 1
    fi

    echo " Unable to access keyvault $KV_NAME after $ATTEMPT/$MAX_ATTEMPTS. Waiting for network rules to take effect."
    sleep 5
    ((ATTEMPT++))

  done

}

function kv_remove_network_exception() {

  # set up variables
  #
  local KV_NAME
  KV_NAME=$(get_kv_name)

  echo -e "\nSetting key vault $KV_NAME back to private access..."

  # ensure kv exists
  #
  if ! does_kv_exist "$KV_NAME"; then
    return 0   # don't cause outer sourced script to fail
  fi

  # ensure resource group isn't being deleted
  #
  if is_kv_rg_deleting "$KV_NAME"; then
    return 0   # don't cause outer sourced script to fail
  fi

  # Always disable public network access after deployment
  # Private endpoint is used during normal TRE operation
  az keyvault update --name "$KV_NAME" --public-network-access Disabled --output none
  echo -e " Key vault set back to private access\n"
}


function get_kv_name() {

  local TRE_ID_LOCAL="${TRE_ID:-}"

  if [[ -z "$TRE_ID_LOCAL" ]]; then
    if [[ "${core_tre_rg:-}" == rg-* ]]; then  # TRE_ID may not be available when called from destroy_env_no_terraform.sh
      TRE_ID_LOCAL="${core_tre_rg#rg-}"
    fi
  fi

  if [[ -z "$TRE_ID_LOCAL" ]]; then
    echo -e "Could not add/remove keyvault network access: TRE_ID is not set\nExiting...\n"
    exit 1
  fi

  echo "kv-${TRE_ID_LOCAL}"
}

function does_kv_exist() {

  KV_NAME=$1

  if [[ -z "$(az keyvault list --query "[?name=='$KV_NAME'].id" --output tsv)" ]]; then
      echo -e " Core key vault $KV_NAME not found\n"
      return 1
  fi

  return 0
}

function is_kv_rg_deleting() {

  KV_NAME=$1

  local KV_RG_NAME
  KV_RG_NAME=$(az keyvault show --name "$KV_NAME" --query "resourceGroup" -o tsv)

  if [[ "$(az group show --name "${KV_RG_NAME}" --query "properties.provisioningState" -o tsv)" == "Deleting" ]]; then
    echo -e " Resource group ${KV_RG_NAME} is being deleted\n"
    return 0
  fi

  return 1
}


# setup the trap to remove network exception on exit
add_exit_trap "kv_remove_network_exception"

# now add the network exception
kv_add_network_exception "$@"
