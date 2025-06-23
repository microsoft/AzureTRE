#!/bin/bash

#
# Add an exception to the TRE management storage account by making it public for deployment, and remove it on script exit.
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"

# Global variable to capture underlying error
LAST_PUBLIC_ACCESS_ERROR=""

# Prevent the script from running multiple times within the current shell
if [ -n "${MGMTSTORAGE_PUBLIC_ACCESS_SCRIPT_GUARD+x}" ]; then
  echo -e "\nEnabling public access on storage account script already executed in current shell, not running again.\n"
  return 0
else
  export MGMTSTORAGE_PUBLIC_ACCESS_SCRIPT_GUARD=true # export so guard is visible in sub shells
  add_exit_trap "mgmtstorage_disable_public_access"
fi

function mgmtstorage_enable_public_access() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  # Check that the storage account exists before making changes
  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n" >&2#!/bin/bash

#
# Add an exception to the TRE management storage account by making it public for deployment, and remove it on script exit.
#
# Note: Ensure you "source" this script, or else the EXIT trap won't fire at the right time.
#

# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/bash_trap_helper.sh"

# Global variable to capture underlying error
LAST_PUBLIC_ACCESS_ERROR=""

# Only register the exit trap once per shell session
if [ -z "${MGMTSTORAGE_PUBLIC_ACCESS_SCRIPT_GUARD+x}" ]; then
  export MGMTSTORAGE_PUBLIC_ACCESS_SCRIPT_GUARD=true
  add_exit_trap "mgmtstorage_disable_public_access"
fi

function mgmtstorage_enable_public_access() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nEnabling public access on storage account $SA_NAME with resource group $RESOURCE_GROUP"

  if ! retry_az_command az storage account update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SA_NAME" \
    --public-network-access Enabled \
    --default-action Allow \
    --output none; then
    echo -e "Error: Failed to enable public access on $SA_NAME\n"
    exit 1
  fi

  for ATTEMPT in {1..10}; do
    if is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
      echo -e " Storage account $SA_NAME is now publicly accessible\n"
      break
    fi
    echo " Unable to confirm public access on $SA_NAME after $ATTEMPT/10. Retrying..."
    sleep 10
  done

  # Assign Storage Blob Data Contributor to the current user
  assign_blob_data_contributor_to_current_user "$SA_NAME" "$RESOURCE_GROUP"
}
function mgmtstorage_disable_public_access() {
  local RESOURCE_GROUP
  RESOURCE_GROUP=$(get_resource_group_name)

  local SA_NAME
  SA_NAME=$(get_storage_account_name)

  if ! does_storage_account_exist "$SA_NAME"; then
    echo -e "Error: Storage account $SA_NAME does not exist.\n" >&2
    exit 1
  fi

  echo -e "\nDisabling public access on storage account $SA_NAME"

  if ! retry_az_command az storage account update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SA_NAME" \
    --public-network-access Disabled \
    --default-action Deny \
    --output none; then
    echo -e "Error: Failed to disable public access on $SA_NAME\n"
    exit 1
  fi

  for ATTEMPT in {1..10}; do
    if ! is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
      echo -e " Public access has been disabled successfully\n"
      return
    fi
    echo " Unable to confirm public access is disabled on $SA_NAME after $ATTEMPT/10. Retrying..."
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
  [[ -n "$(az storage account show --name "$1" --query "id" --output tsv 2>/dev/null)" ]]
}

function is_public_access_enabled() {
  local RESOURCE_GROUP="$1"
  local SA_NAME="$2"
  LAST_PUBLIC_ACCESS_ERROR=""

  local access
  if ! access=$(az storage account show --name "$SA_NAME" --resource-group "$RESOURCE_GROUP" --query "publicNetworkAccess" --output tsv 2>/dev/null); then
    LAST_PUBLIC_ACCESS_ERROR="Failed to get public access status for $SA_NAME"
    return 1
  fi

  echo -e "Status of public access for storage account $SA_NAME: $access"

  if [[ "$access" == "Enabled" ]]; then
    return 0
  else
    LAST_PUBLIC_ACCESS_ERROR="publicNetworkAccess is not Enabled"
    return 1
  fi
}

function retry_az_command() {
  local cmd=("$@")
  local attempt=0
  local max_attempts=5

  until "${cmd[@]}"; do
    attempt=$((attempt + 1))
    if (( attempt >= max_attempts )); then
      echo "Command failed after $max_attempts attempts: ${cmd[*]}"
      return 1
    fi
    echo "Retrying command (${attempt}/${max_attempts})..."
    sleep $((2 ** attempt))
  done
}

# Always enable public access, even if script sourced before
mgmtstorage_enable_public_access "$@"

    exit 1
  fi

  echo -e "\nEnabling public access on storage account $SA_NAME with resource group $RESOURCE_GROUP"

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
  echo -e "$LAST_PUBLIC_ACCESS_ERROR\n"
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

function assign_blob_data_contributor_to_current_user() {
  local SA_NAME="$1"
  local RESOURCE_GROUP="$2"

  echo -e "\nAssigning 'Storage Blob Data Contributor' role to current user for storage account $SA_NAME..."

  local CURRENT_USER_OBJECT_ID
  CURRENT_USER_OBJECT_ID=$(az ad signed-in-user show --query objectId -o tsv 2>/dev/null)

  if [[ -z "$CURRENT_USER_OBJECT_ID" ]]; then
    echo "Error: Could not get current user's object ID. Make sure you are logged in with 'az login' and have 'az ad' permission." >&2
    return 1
  fi

  local SCOPE
  SCOPE=$(az storage account show --name "$SA_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

  if ! az role assignment create \
    --assignee-object-id "$CURRENT_USER_OBJECT_ID" \
    --assignee-principal-type User \
    --role "Storage Blob Data Contributor" \
    --scope "$SCOPE" \
    --output none; then
    echo "Error: Failed to assign Storage Blob Data Contributor role to user." >&2
    return 1
  fi

  echo "Successfully assigned role to user."
}

function is_public_access_enabled() {
  local RESOURCE_GROUP="$1"
  local SA_NAME="$2"
  LAST_PUBLIC_ACCESS_ERROR=""

  local access
  if ! access=$(az storage account show --name "$SA_NAME" --resource-group "$RESOURCE_GROUP" --query "publicNetworkAccess" --output tsv 2>/dev/null); then
    LAST_PUBLIC_ACCESS_ERROR="Failed to get public access status for $SA_NAME"
    return 1
  fi

  echo -e "Status of public access for storage account $SA_NAME: $access"

  if [[ "$access" == "Enabled" ]]; then
    return 0
  else
    LAST_PUBLIC_ACCESS_ERROR="publicNetworkAccess is not Enabled"
    return 1
  fi
}

# Enable public access for deployment
mgmtstorage_enable_public_access "$@"
