#!/bin/bash

#
# Add an exception to the TRE management storage account by making it public for deployment, and remove it on script exit.
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

function mgmtstorage_enable_public_access() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n" >&2
    exit 1
  fi

  # Pre-check: if public access is already enabled, no need to update.
  if is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
    echo -e " Storage account $SA_NAME is already publicly accessible\n"
    return
  fi

  echo -e "\nEnabling public access on storage account $SA_NAME"

  # Enable public network access with explicit default action allow
  az storage account update --resource-group "$RESOURCE_GROUP" --name "$SA_NAME" --public-network-access Enabled --default-action Allow --output none

  for ATTEMPT in {1..10}; do
    if is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
      echo -e " Storage account $SA_NAME is now publicly accessible\n"
      return
    fi

    echo " Unable to confirm public access on storage account $SA_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not enable public access for $SA_NAME after 10 attempts.\n"
  exit 1
}

function mgmtstorage_disable_public_access() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n" >&2
    exit 1
  fi

  # Pre-check: if public access is already disabled, no need to update.
  if ! is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
    echo -e " Storage account $SA_NAME is already not publicly accessible\n"
    return
  fi

  echo -e "\nDisabling public access on storage account $SA_NAME"

  # Disable public network access with explicit default action deny
  az storage account update --resource-group "$RESOURCE_GROUP" --name "$SA_NAME" --public-network-access Disabled --default-action Deny --output none

  for ATTEMPT in {1..10}; do
    if ! is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
      echo -e " Public access has been disabled successfully\n"
      return
    fi

    echo " Unable to confirm public access is disabled on storage account $SA_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not disable public access for $SA_NAME after 10 attempts.\n"
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

function does_storage_account_exist() {
  [[ -n "$(az storage account show --name "$1" --query "id" --output tsv)" ]]
}

function is_public_access_enabled() {
  local RESOURCE_GROUP="$1"
  local SA_NAME="$2"

  # Try listing containers
  local containers
  if ! containers=$(az storage container list --account-name "$SA_NAME" --auth-mode login --query "[].name" --output tsv); then
    return 1
  fi

  # For each container found, check blob listing
  for container in $containers; do
    if ! az storage blob list --container-name "$container" --account-name "$SA_NAME" --auth-mode login --output none; then
      return 1
    fi
  done

  # If container list succeeded (even if empty) and blob list (if any) succeeded, public access is enabled
  return 0
}

# Setup the trap to disable public access on exit
trap mgmtstorage_disable_public_access EXIT

# Enable public access for deployment
mgmtstorage_enable_public_access "$@"
