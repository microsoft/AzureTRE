#!/bin/bash

#
# Add an IP exception to the Key Vault firewall for deployment, and remove on script exit
# The current machine's IP address is used, or $PUBLIC_DEPLOYMENT_IP_ADDRESS if set
#
# Note:  Ensure you "source" this script, or else the EXIT trap won't fire at the right time
#


function kv_add_network_exception() {

  # set up variables
  #
  local KV_NAME
  KV_NAME=$(get_kv_name)

  local MY_IP
  MY_IP=$(get_my_ip)

  echo -e "\nAdding deployment network exception to key vault $KV_NAME..."

  # ensure kv exists
  #
  if ! does_kv_exist "$KV_NAME"; then
    return 0   # don't cause outer sourced script to fail
  fi

  # add keyvault network exception
  #
  az keyvault network-rule add --name "$KV_NAME" --ip-address "$MY_IP" --output none

  local ATTEMPT=1
  local MAX_ATTEMPTS=10

  while true; do

    if KV_OUTPUT=$(az keyvault secret list --vault-name "$KV_NAME" --query '[].name' --output tsv 2>&1); then
      echo -e " Keyvault $KV_NAME is now accessible\n"
      break
    fi

    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
      echo -e "Could not add deployment network exception for $KV_NAME"
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

  local MY_IP
  MY_IP=$(get_my_ip)

  echo -e "\nRemoving deployment network exception to key vault $KV_NAME..."

  # ensure kv exists
  #
  if ! does_kv_exist "$KV_NAME"; then
    return 0   # don't cause outer sourced script to fail
  fi

  # ensure resource group isn't being deleted
  #
  if is_core_rg_deleting; then
    return 0   # don't cause outer sourced script to fail
  fi

  # remove keyvault network exception
  #
  az keyvault network-rule remove --name "$KV_NAME" --ip-address "$MY_IP" --output none
  echo -e " Deployment network exception removed\n"
}


function get_kv_name() {

  local TRE_ID_LOCAL="${TRE_ID:-}"

  if [[ -z "$TRE_ID_LOCAL" ]]; then
    if [[ "${core_tre_rg:-}" == rg-* ]]; then  # TRE_ID may not be available when called from destroy_env_no_terraform.sh
      TRE_ID_LOCAL="${core_tre_rg#rg-}"
    fi
  fi

  if [[ -z "$TRE_ID_LOCAL" ]]; then
    echo -e "Could not add/remove keyvault deployment network exception: TRE_ID is not set\nExiting...\n"
    exit 1
  fi

  echo "kv-${TRE_ID_LOCAL}"
}

function get_my_ip() {

  local MY_IP="${PUBLIC_DEPLOYMENT_IP_ADDRESS:-}"

  if [[ -z "$MY_IP" ]]; then
    MY_IP=$(curl -s "ipecho.net/plain"; echo)
  fi

  echo "$MY_IP"
}

function does_kv_exist() {

  KV_NAME=$1

  if [[ -z "$(az keyvault list --query "[?name=='$KV_NAME'].id" --output tsv)" ]]; then
      echo -e " Core key vault $KV_NAME not found\n"
      return 1
  fi

  return 0
}

function is_core_rg_deleting() {
  if [[ "$(az group show --name "${core_tre_rg:-}" --query "properties.provisioningState" -o tsv)" == "Deleting" ]]; then
    echo -e " Resource group ${core_tre_rg:-} is being deleted\n"
    return 0
  fi

  return 1
}


# setup the trap to remove network exception on exit
trap kv_remove_network_exception EXIT

# now add the network exception
kv_add_network_exception "$@"
