#!/bin/bash

#
# Add an exception to a storage account by making it public for deployment, and remove it on script exit.
#
# Usage: source storage_enable_public_access.sh --storage-account-name <n> --resource-group-name <rg>
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"

# Global variable for error tracking
LAST_PUBLIC_ACCESS_ERROR=""

function storage_enable_public_access() {
  local storage_account_name="$1"
  local resource_group_name="$2"

  echo -e "\nEnabling public access on storage account"
  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$storage_account_name"; then
    echo -e "Error: Storage account $storage_account_name does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nEnabling public access on storage account $storage_account_name"

  # Enable public network access with explicit default action allow
  az storage account update --resource-group "$resource_group_name" --name "$storage_account_name" --public-network-access Enabled --default-action Allow --output none

  for ATTEMPT in {1..10}; do
    if is_public_access_enabled "$storage_account_name"; then
      echo -e " Storage account $storage_account_name is now publicly accessible\n"
      return
    fi

    echo " Unable to confirm public access on storage account $storage_account_name after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not enable public access for $storage_account_name after 10 attempts.\n"
  echo -e "$LAST_PUBLIC_ACCESS_ERROR\n"
  exit 1
}

function storage_disable_public_access() {
  local storage_account_name="$1"
  local resource_group_name="$2"

  echo -e "\nDisabling public access on storage account"
  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$storage_account_name"; then
    echo -e "Error: Storage account $storage_account_name does not exist.\n" >&2
    return 1
  fi

  echo -e "\nStorage account name: $storage_account_name"
  echo -e "\nResource group name: $resource_group_name"

  # Disable public network access with explicit default action deny
  az storage account update --resource-group "$resource_group_name" --name "$storage_account_name" --public-network-access Disabled --default-action Deny --output none

  for ATTEMPT in {1..10}; do
    if ! is_public_access_enabled "$storage_account_name"; then
      echo -e " Public access has been disabled successfully\n"
      # Clean up the guard variable for this storage account
      STORAGE_GUARD_VAR="STORAGE_PUBLIC_ACCESS_SCRIPT_GUARD_${storage_account_name}"
      unset "$STORAGE_GUARD_VAR"
      return
    fi

    echo " Unable to confirm public access is disabled on storage account $storage_account_name after $ATTEMPT/10. Waiting for update to take effect..."
    sleep 10
  done

  echo -e "Error: Could not disable public access for $storage_account_name after 10 attempts.\n"
  return 1
}

function does_storage_account_exist() {
  [[ -n "$(az storage account show --name "$1" --query "id" --output tsv 2>/dev/null)" ]]
}

function is_public_access_enabled() {
  local storage_account_name="$1"
  LAST_PUBLIC_ACCESS_ERROR=""

  # Try listing containers and capture error output
  local containers
  if ! containers=$(az storage container list --account-name "$storage_account_name" --auth-mode login --query "[].name" --output tsv 2>&1); then
    LAST_PUBLIC_ACCESS_ERROR="$containers"
    return 1
  fi

  # For each container found, check blob listing and capture error if any
  for container in $containers; do
    local blob_output
    if ! blob_output=$(az storage blob list --container-name "$container" --account-name "$storage_account_name" --auth-mode login --output none 2>&1); then
      LAST_PUBLIC_ACCESS_ERROR="$blob_output"
      return 1
    fi
  done

  # If container list succeeded (even if empty) and blob list (if any) succeeded, public access is enabled
  return 0
}

# Main execution
# Parse arguments inline
storage_account_name=""
resource_group_name=""

while [ "$1" != "" ]; do
  case $1 in
  --storage-account-name)
    shift
    storage_account_name=$1
    ;;
  --resource-group-name)
    shift
    resource_group_name=$1
    ;;
  *)
    echo "Unexpected argument: '$1'"
    echo "Usage: storage_enable_public_access.sh --storage-account-name <n> --resource-group-name <rg>"
    exit 1
    ;;
  esac

  if [[ -z "${2:-}" ]]; then
    # if no more args then stop processing
    break
  fi

  shift # remove the current value for `$1` and use the next
done

# Validate arguments inline
if [[ -z "${storage_account_name:-}" ]]; then
  echo "Error: --storage-account-name argument is required" >&2
  exit 1
fi

if [[ -z "${resource_group_name:-}" ]]; then
  echo "Error: --resource-group-name argument is required" >&2
  exit 1
fi

# Prevent the script from running multiple times for the same storage account within the current shell
STORAGE_GUARD_VAR="STORAGE_PUBLIC_ACCESS_SCRIPT_GUARD_${storage_account_name}"
if [ -n "${!STORAGE_GUARD_VAR+x}" ]; then
  echo -e "\nEnabling public access on storage account $storage_account_name already executed in current shell, not running again.\n"
  return 0
fi
export "$STORAGE_GUARD_VAR"=true # export so guard is visible in sub shells

# Setup the trap to disable public access on exit (only on first run)
# Capture the current values to avoid conflicts with subsequent calls
add_exit_trap "storage_disable_public_access '$storage_account_name' '$resource_group_name'"

# Enable public access for deployment
storage_enable_public_access "$storage_account_name" "$resource_group_name"
