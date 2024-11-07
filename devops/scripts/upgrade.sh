#!/bin/bash
set -e

# This script is used to upgrade terraform providers in a specified directory

# Usage: ./upgrade.sh <directory>

DIR=$1

# Load environment variables from .env file
if [ -f "$DIR/.env" ]; then
  set -a
  . "$DIR/.env"
  set +a
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

# Run terraform init with upgrade and reconfigure options
terraform -chdir="$DIR/terraform" init -upgrade -reconfigure -input=false -backend=true \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${KEY}"
