#!/bin/bash

#
# Add an IP exception to the TRE management storage account for deployment, and remove it on script exit.
# Uses the current machine's IP or $PUBLIC_DEPLOYMENT_IP_ADDRESS if set.
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

function mgmtstorage_add_network_exception() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  local MY_IP
  MY_IP=$(get_my_ip)

  echo -e "\nAdding deployment network exception to storage account $SA_NAME..."

  # Ensure storage account exists
  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n"
    return 0  # Don't cause outer sourced script to fail
  fi

  # Add storage account network exception
  az storage account network-rule add --resource-group "$RESOURCE_GROUP" --account-name "$SA_NAME" --ip-address "$MY_IP" --output none

  for ATTEMPT in {1..10}; do
    if is_ip_in_network_rule "$RESOURCE_GROUP" "$SA_NAME" "$MY_IP"; then
      echo -e " Storage account $SA_NAME is now accessible\n"
      return
    fi

    echo " Unable to access storage account $SA_NAME after $ATTEMPT/10. Waiting for network rules to take effect..."
    sleep 5
  done

  echo -e "Error: Could not add deployment network exception for $SA_NAME after 10 attempts.\n"
  exit 1
}

function mgmtstorage_remove_network_exception() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  local MY_IP
  MY_IP=$(get_my_ip)

  echo -e "\nRemoving deployment network exception from storage account $SA_NAME..."

  # Ensure storage account exists
  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n"
    return 0  # Don't cause outer sourced script to fail
  fi

  # Remove storage account network exception
  az storage account network-rule remove --resource-group "$RESOURCE_GROUP" --account-name "$SA_NAME" --ip-address "$MY_IP" --output none

  for ATTEMPT in {1..10}; do
    if ! is_ip_in_network_rule "$RESOURCE_GROUP" "$SA_NAME" "$MY_IP"; then
      echo -e " Deployment network exception removed successfully\n"
      return
    fi

    echo " Unable to remove network exception for storage account $SA_NAME after $ATTEMPT/10. Waiting for network rules to take effect..."
    sleep 5
  done

  echo -e "Error: Could not remove deployment network exception for $SA_NAME after 10 attempts.\n"
  exit 1
}

function get_resource_group_name() {
  if [[ -z "${TF_VAR_mgmt_resource_group_name:-}" ]]; then
    echo -e "Error: TF_VAR_mgmt_resource_group_name is not set\nExiting...\n" >&2
    exit 1
  fi
  echo "$TF_VAR_mgmt_resource_group_name"
}

function get_storage_account_name() {
  if [[ -z "${TF_VAR_mgmt_storage_account_name:-}" ]]; then
    echo -e "Error: TF_VAR_mgmt_storage_account_name is not set\nExiting...\n" >&2
    exit 1
  fi
  echo "$TF_VAR_mgmt_storage_account_name"
}

function get_my_ip() {
  if [[ -n "${PUBLIC_DEPLOYMENT_IP_ADDRESS:-}" ]]; then
    echo "$PUBLIC_DEPLOYMENT_IP_ADDRESS"
  else
    local MY_IP
    MY_IP=$(curl -s "https://ipecho.net/plain") || { echo "Error: Failed to fetch IP address" >&2; exit 1; }

    if [[ -z "$MY_IP" ]]; then
      echo "Error: Could not determine IP address." >&2
      exit 1
    fi

    echo "$MY_IP"
  fi
}

function does_storage_account_exist() {
  [[ -n "$(az storage account show --name "$1" --query "id" --output tsv)" ]]
}

function is_ip_in_network_rule() {
  local RESOURCE_GROUP="$1"
  local SA_NAME="$2"
  local MY_IP="$3"

  # Step 1: Check if the IP is present in the network rules
  local COUNT
  COUNT=$(az storage account network-rule list --resource-group "$RESOURCE_GROUP" --account-name "$SA_NAME" --query "length(ipRules[?ipAddressOrRange=='$MY_IP'])" --output tsv)

  if [[ "$COUNT" -gt 0 ]]; then
    # Step 2: Verify storage accessibility by listing containers...
    containers=$(az storage container list --account-name "$SA_NAME" --auth-mode login --query "[].name" --output tsv)
    if [[ -z "$containers" ]]; then
      # No containers found, assume success.
      return 0
    fi
    for container in $containers; do
      if ! az storage blob list --container-name "$container" --account-name "$SA_NAME" --auth-mode login --output none; then
        return 1  # Failure if blob listing fails in any container
      fi
    done
    return 0  # Success if blob list works for all containers
  fi

  return 1  # Either rule not added or access is still restricted
}

# Setup the trap to remove the network exception on exit
trap mgmtstorage_remove_network_exception EXIT

# Add the network exception
mgmtstorage_add_network_exception "$@"
