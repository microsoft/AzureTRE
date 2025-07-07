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

# The storage account is protected by network rules
echo "Enabling public access to storage account..."
az storage account update --default-action Allow --name "${STORAGE_ACCOUNT}"
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

echo "Disabling public access to storage account..."
az storage account update --default-action Deny --name "${STORAGE_ACCOUNT}"
