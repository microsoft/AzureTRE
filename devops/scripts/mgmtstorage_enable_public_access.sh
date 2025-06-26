#!/bin/bash

#
# Add an exception to a storage account by making it public for deployment, and remove it on script exit.
# 
# This script can be used in two ways:
# 1. For TRE management storage account (backward compatibility): Set environment variables TF_VAR_mgmt_resource_group_name and TF_VAR_mgmt_storage_account_name
# 2. For any storage account: Pass --storage-account-name and --resource-group-name arguments
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"

# Global variables
LAST_PUBLIC_ACCESS_ERROR=""
STORAGE_ACCOUNT_NAME=""
RESOURCE_GROUP_NAME=""

# Parse command line arguments
function parse_arguments() {
  while [ "$1" != "" ]; do
    case $1 in
    --storage-account-name)
      shift
      STORAGE_ACCOUNT_NAME=$1
      ;;
    --resource-group-name)
      shift
      RESOURCE_GROUP_NAME=$1
      ;;
    *)
      echo "Unexpected argument: '$1'"
      echo "Usage: mgmtstorage_enable_public_access.sh [--storage-account-name <name> --resource-group-name <rg>]"
      echo "If no arguments provided, uses TF_VAR_mgmt_resource_group_name and TF_VAR_mgmt_storage_account_name environment variables"
      exit 1
      ;;
    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next
  done
}

# Initialize storage account and resource group names
function initialize_names() {
  # If command line arguments weren't provided, use environment variables (backward compatibility)
  if [[ -z "${STORAGE_ACCOUNT_NAME:-}" ]]; then
    STORAGE_ACCOUNT_NAME=$(get_mgmt_storage_account_name)
  fi
  
  if [[ -z "${RESOURCE_GROUP_NAME:-}" ]]; then
    RESOURCE_GROUP_NAME=$(get_mgmt_resource_group_name)
  fi
}

# Prevent the script from running multiple times within the current shell
if [ -n "${STORAGE_PUBLIC_ACCESS_SCRIPT_GUARD+x}" ]; then
  echo -e "\nEnabling public access on storage account script already executed in current shell, not running again.\n"
  return 0
fi
export STORAGE_PUBLIC_ACCESS_SCRIPT_GUARD=true # export so guard is visible in sub shells

function storage_enable_public_access() {
  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$STORAGE_ACCOUNT_NAME"; then
    echo -e "Error: Storage account $STORAGE_ACCOUNT_NAME does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nEnabling public access on storage account $STORAGE_ACCOUNT_NAME"

  # Enable public network access with explicit default action allow
  az storage account update --resource-group "$RESOURCE_GROUP_NAME" --name "$STORAGE_ACCOUNT_NAME" --public-network-access Enabled --default-action Allow --output none

  for ATTEMPT in {1..10}; do
    if is_public_access_enabled "$STORAGE_ACCOUNT_NAME"; then
      echo -e " Storage account $STORAGE_ACCOUNT_NAME is now publicly accessible\n"
      return
    fi

    echo " Unable to confirm public access on storage account $STORAGE_ACCOUNT_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not enable public access for $STORAGE_ACCOUNT_NAME after 10 attempts.\n"
  echo -e "$LAST_PUBLIC_ACCESS_ERROR\n"
  exit 1
}

function storage_disable_public_access() {
  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$STORAGE_ACCOUNT_NAME"; then
    echo -e "Error: Storage account $STORAGE_ACCOUNT_NAME does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nDisabling public access on storage account $STORAGE_ACCOUNT_NAME"

  # Disable public network access with explicit default action deny
  az storage account update --resource-group "$RESOURCE_GROUP_NAME" --name "$STORAGE_ACCOUNT_NAME" --public-network-access Disabled --default-action Deny --output none

  for ATTEMPT in {1..10}; do
    if ! is_public_access_enabled "$STORAGE_ACCOUNT_NAME"; then
      echo -e " Public access has been disabled successfully\n"
      return
    fi

    echo " Unable to confirm public access is disabled on storage account $STORAGE_ACCOUNT_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not disable public access for $STORAGE_ACCOUNT_NAME after 10 attempts.\n"
  exit 1
}

function get_mgmt_resource_group_name() {
  if [[ -z "${TF_VAR_mgmt_resource_group_name:-}" ]]; then
    echo -e "Error: TF_VAR_mgmt_resource_group_name is not set\nExiting...\n" >&2
    exit 1
  fi
  echo "$TF_VAR_mgmt_resource_group_name"
}

function get_mgmt_storage_account_name() {
  if [[ -z "${TF_VAR_mgmt_storage_account_name:-}" ]]; then
    echo -e "Error: TF_VAR_mgmt_storage_account_name is not set\nExiting...\n" >&2
    exit 1
  fi
  echo "$TF_VAR_mgmt_storage_account_name"
}

function does_storage_account_exist() {
  [[ -n "$(az storage account show --name "$1" --query "id" --output tsv 2>/dev/null)" ]]
}

function is_public_access_enabled() {
  local SA_NAME="$1"
  LAST_PUBLIC_ACCESS_ERROR=""

  # Try listing containers and capture error output
  local containers
  if ! containers=$(az storage container list --account-name "$SA_NAME" --auth-mode login --query "[].name" --output tsv 2>&1); then
    LAST_PUBLIC_ACCESS_ERROR="$containers"
    return 1
  fi

  # For each container found, check blob listing and capture error if any
  for container in $containers; do
    local blob_output
    if ! blob_output=$(az storage blob list --container-name "$container" --account-name "$SA_NAME" --auth-mode login --output none 2>&1); then
      LAST_PUBLIC_ACCESS_ERROR="$blob_output"
      return 1
    fi
  done

  # If container list succeeded (even if empty) and blob list (if any) succeeded, public access is enabled
  return 0
}

# Main execution
parse_arguments "$@"
initialize_names

# Setup the trap to disable public access on exit
add_exit_trap "storage_disable_public_access"

# Enable public access for deployment
storage_enable_public_access
