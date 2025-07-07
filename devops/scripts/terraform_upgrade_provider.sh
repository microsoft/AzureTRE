#!/bin/bash
set -e

# This script is used to upgrade terraform providers in a specified directory

# Usage: ./upgrade.sh <directory>

DIR=$1

# Load environment variables from .env file
if [ -f "$DIR/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$DIR/.env"
  set +a
fi

# Ensure TF_VAR_mgmt_resource_group_name is set
if [ -z "${TF_VAR_mgmt_resource_group_name}" ]; then
  echo "Error: TF_VAR_mgmt_resource_group_name is not set."
  exit 1
fi

# Ensure TF_VAR_mgmt_storage_account_name is set
if [ -z "${TF_VAR_mgmt_storage_account_name}" ]; then
  echo "Error: TF_VAR_mgmt_storage_account_name is not set."
  exit 1
fi

# Ensure TF_VAR_terraform_state_container_name is set
if [ -z "${TF_VAR_terraform_state_container_name}" ]; then
  echo "Error: TF_VAR_terraform_state_container_name is not set."
  exit 1
fi

# Ensure TRE_ID is set
if [ -z "${TRE_ID}" ]; then
  echo "Error: TRE_ID is not set."
  exit 1
fi

# Infer the key from the directory names
PARENT_DIR=$(basename "$(dirname "$DIR")")
GRANDPARENT_DIR=$(basename "$(dirname "$(dirname "$DIR")")")

if [[ "$GRANDPARENT_DIR" == "workspaces" || "$GRANDPARENT_DIR" == "shared_services" ]]; then
  KEY="${TRE_ID?}_${TF_VAR_id?}_${PARENT_DIR}"
elif [[ "$GRANDPARENT_DIR" == "workspace_services" ]]; then
  KEY="${TRE_ID?}_${TF_VAR_workspace_id?}_${TF_VAR_id?}_${PARENT_DIR}"
elif [[ "$GRANDPARENT_DIR" == "user_resources" ]]; then
  KEY="${TRE_ID?}_${TF_VAR_workspace_id?}_${TF_VAR_workspace_service_id?}_${TF_VAR_id?}_${PARENT_DIR}"
else
  KEY="${TRE_ID?}_${PARENT_DIR}"
fi

# shellcheck disable=SC1091
source "$(dirname "$0")/storage_enable_public_access.sh" \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}"

# Run terraform init with upgrade and reconfigure options
terraform -chdir="$DIR/terraform" init -upgrade -reconfigure -input=false -backend=true \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${KEY}"
