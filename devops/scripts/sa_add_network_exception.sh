#!/bin/bash

#
# Add an exception to a specific storage account by making it public for deployment, and remove it on script exit.
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"

# Global variable to capture underlying error
LAST_SA_PUBLIC_ACCESS_ERROR=""

# Parse command line arguments
function parse_arguments() {
  while [ "$1" != "" ]; do
    case $1 in
    --storage-account-name)
      shift
      SA_STORAGE_ACCOUNT_NAME=$1
      ;;
    --resource-group-name)
      shift
      SA_RESOURCE_GROUP_NAME=$1
      ;;
    *)
      echo "Unexpected argument: '$1'"
      echo "Usage: sa_add_network_exception.sh --storage-account-name <name> --resource-group-name <rg>"
      exit 1
      ;;
    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next
  done

  # Validate required parameters
  if [[ -z "${SA_STORAGE_ACCOUNT_NAME:-}" ]]; then
    echo "Error: --storage-account-name is required" >&2
    exit 1
  fi

  if [[ -z "${SA_RESOURCE_GROUP_NAME:-}" ]]; then
    echo "Error: --resource-group-name is required" >&2
    exit 1
  fi
}

function sa_enable_public_access() {
  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$SA_STORAGE_ACCOUNT_NAME"; then
    echo -e "Error: Storage account $SA_STORAGE_ACCOUNT_NAME does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nEnabling public access on storage account $SA_STORAGE_ACCOUNT_NAME"

  # Enable public network access with explicit default action allow
  az storage account update --resource-group "$SA_RESOURCE_GROUP_NAME" --name "$SA_STORAGE_ACCOUNT_NAME" --public-network-access Enabled --default-action Allow --output none

  for ATTEMPT in {1..10}; do
    if is_public_access_enabled "$SA_RESOURCE_GROUP_NAME" "$SA_STORAGE_ACCOUNT_NAME"; then
      echo -e " Storage account $SA_STORAGE_ACCOUNT_NAME is now publicly accessible\n"
      return
    fi

    echo " Unable to confirm public access on storage account $SA_STORAGE_ACCOUNT_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not enable public access for $SA_STORAGE_ACCOUNT_NAME after 10 attempts.\n"
  echo -e "$LAST_SA_PUBLIC_ACCESS_ERROR\n"
  exit 1
}

function sa_disable_public_access() {
  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$SA_STORAGE_ACCOUNT_NAME"; then
    echo -e "Error: Storage account $SA_STORAGE_ACCOUNT_NAME does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nDisabling public access on storage account $SA_STORAGE_ACCOUNT_NAME"

  # Disable public network access with explicit default action deny
  az storage account update --resource-group "$SA_RESOURCE_GROUP_NAME" --name "$SA_STORAGE_ACCOUNT_NAME" --public-network-access Disabled --default-action Deny --output none

  for ATTEMPT in {1..10}; do
    if ! is_public_access_enabled "$SA_RESOURCE_GROUP_NAME" "$SA_STORAGE_ACCOUNT_NAME"; then
      echo -e " Public access has been disabled successfully\n"
      return
    fi

    echo " Unable to confirm public access is disabled on storage account $SA_STORAGE_ACCOUNT_NAME after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not disable public access for $SA_STORAGE_ACCOUNT_NAME after 10 attempts.\n"
  exit 1
}

function does_storage_account_exist() {
  [[ -n "$(az storage account show --name "$1" --query "id" --output tsv 2>/dev/null)" ]]
}

function is_public_access_enabled() {
  local SA_NAME="$2"
  LAST_SA_PUBLIC_ACCESS_ERROR=""

  # Try listing containers and capture error output
  local containers
  if ! containers=$(az storage container list --account-name "$SA_NAME" --auth-mode login --query "[].name" --output tsv 2>&1); then
    LAST_SA_PUBLIC_ACCESS_ERROR="$containers"
    return 1
  fi

  # For each container found, check blob listing and capture error if any
  for container in $containers; do
    local blob_output
    if ! blob_output=$(az storage blob list --container-name "$container" --account-name "$SA_NAME" --auth-mode login --output none 2>&1); then
      LAST_SA_PUBLIC_ACCESS_ERROR="$blob_output"
      return 1
    fi
  done

  # If container list succeeded (even if empty) and blob list (if any) succeeded, public access is enabled
  return 0
}

# Main execution
parse_arguments "$@"

# Setup the trap to disable public access on exit
add_exit_trap "sa_disable_public_access"

# Enable public access for deployment
sa_enable_public_access
