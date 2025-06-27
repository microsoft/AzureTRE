#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

if [[ -z ${STORAGE_ACCOUNT:-} ]]; then
  echo "STORAGE_ACCOUNT not set"
  exit 1
fi

if [[ -z ${RESOURCE_GROUP_NAME:-} ]]; then
  echo "RESOURCE_GROUP_NAME not set"
  exit 1
fi

# The storage account is protected by network rules
# Use the standardized script with exit trap to ensure cleanup
# shellcheck disable=SC1091
source "$(dirname "${BASH_SOURCE[0]}")/storage_enable_public_access.sh" \
  --storage-account-name "${STORAGE_ACCOUNT}" \
  --resource-group-name "${RESOURCE_GROUP_NAME}"

echo "Waiting for network rule to take effect"
sleep 30

echo "Uploading ${CONTENT_DIR} to static web storage"

# shellcheck disable=SC2016
az storage blob upload-batch \
    --account-name "${STORAGE_ACCOUNT}" \
    --auth-mode login \
    --destination '$web' \
    --source "${CONTENT_DIR}" \
    --no-progress \
    --only-show-errors \
    --overwrite

# No need for manual cleanup - exit trap handles it automatically
