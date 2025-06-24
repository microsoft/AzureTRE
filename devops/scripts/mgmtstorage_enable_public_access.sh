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

  # Use retry logic for the storage account update
  if ! retry_az_command az storage account update \
    --resource-group "$RESOURCE_GROUP" \
    --name "$SA_NAME" \
    --public-network-access Enabled \
    --default-action Allow \
    --output none; then
    echo -e "Error: Failed to enable public access on $SA_NAME\n"
    exit 1
  fi

  # Wait for public access to be confirmed with exponential backoff
  for ATTEMPT in {1..15}; do
    if is_public_access_enabled "$RESOURCE_GROUP" "$SA_NAME"; then
      echo -e " Storage account $SA_NAME is now publicly accessible"

      # Additional wait for Azure backend propagation
      echo " Waiting 30 seconds for Azure backend propagation..."
      sleep 30

      # Test actual blob access
      if test_blob_access "$SA_NAME"; then
        echo -e " Blob access confirmed\n"
        break
      fi
    fi

    local wait_time=$((ATTEMPT * 5))
    echo " Unable to confirm public access on $SA_NAME after $ATTEMPT/15. Waiting ${wait_time}s..."
    sleep $wait_time
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

function assign_blob_data_contributor_to_current_user() {
  local SA_NAME="$1"
  local RESOURCE_GROUP="$2"

  echo -e "\nAssigning 'Storage Blob Data Contributor' role to current account for storage account $SA_NAME..."

  local SCOPE
  SCOPE=$(az storage account show --name "$SA_NAME" --resource-group "$RESOURCE_GROUP" --query id -o tsv)

  # Get current account information
  local ACCOUNT_INFO
  ACCOUNT_INFO=$(az account show --output json 2>/dev/null)

  if [[ -z "$ACCOUNT_INFO" ]]; then
    echo "Error: Could not get current account information. Make sure you are logged in with 'az login'." >&2
    return 1
  fi

  # Check if we're using a service principal or user account
  local ACCOUNT_TYPE
  ACCOUNT_TYPE=$(echo "$ACCOUNT_INFO" | jq -r '.user.type // empty')

  if [[ "$ACCOUNT_TYPE" == "servicePrincipal" ]]; then
    # We're using a service principal
    local SP_CLIENT_ID
    SP_CLIENT_ID=$(echo "$ACCOUNT_INFO" | jq -r '.user.name // empty')

    if [[ -z "$SP_CLIENT_ID" ]]; then
      echo "Error: Could not get service principal client ID." >&2
      return 1
    fi

    echo "Detected service principal: $SP_CLIENT_ID"

    # Assign role using service principal client ID
    if ! az role assignment create \
      --assignee "$SP_CLIENT_ID" \
      --role "Storage Blob Data Contributor" \
      --scope "$SCOPE" \
      --output none 2>/dev/null; then
      echo "Note: Storage Blob Data Contributor role assignment failed or already exists. Continuing..." >&2
    else
      echo "Successfully assigned Storage Blob Data Contributor role to service principal."
    fi

  else
    # We're using a user account
    local CURRENT_USER_OBJECT_ID
    CURRENT_USER_OBJECT_ID=$(az ad signed-in-user show --query id -o tsv 2>/dev/null)

    if [[ -z "$CURRENT_USER_OBJECT_ID" ]]; then
      echo "Error: Could not get current user's object ID. Make sure you have 'az ad' permission." >&2
      return 1
    fi

    echo "Detected user account: $CURRENT_USER_OBJECT_ID"

    # Assign role using user object ID
    if ! az role assignment create \
      --assignee-object-id "$CURRENT_USER_OBJECT_ID" \
      --assignee-principal-type User \
      --role "Storage Blob Data Contributor" \
      --scope "$SCOPE" \
      --output none 2>/dev/null; then
      echo "Note: Storage Blob Data Contributor role assignment failed or already exists. Continuing..." >&2
    else
      echo "Successfully assigned Storage Blob Data Contributor role to user."
    fi
  fi
}

function test_blob_access() {
  local SA_NAME="$1"
  local CONTAINER_NAME="${TF_VAR_terraform_state_container_name}"

  echo "Testing blob access to container $CONTAINER_NAME..."

  # Try to list blobs - this is what Terraform does
  if az storage blob list \
    --account-name "$SA_NAME" \
    --container-name "$CONTAINER_NAME" \
    --auth-mode login \
    --output none 2>/dev/null; then
    return 0
  else
    echo "Blob access test failed, but this might be expected if container is empty"
    return 1
  fi
}

# Always enable public access when script is sourced
mgmtstorage_enable_public_access "$@"
