#!/bin/bash
set -e

script_dir=$(realpath $(dirname "${BASH_SOURCE[0]}"))

if [[ -z ${STORAGE_ACCOUNT} ]]; then
  echo "STORAGE_ACCOUNT not set"
  exit 1
fi

IPADDR=$(curl ipecho.net/plain; echo)

# The storage account is protected by network rules
# The rules need to be temporarily lifted so that the index.html file, if required, and certificate can be uploaded
echo "Creating network rule on storage account ${STORAGE_ACCOUNT} for $IPADDR"
az storage account network-rule add --account-name "${STORAGE_ACCOUNT}" --ip-address $IPADDR
echo "Waiting for network rule to take effect"
sleep 30s
echo "Created network rule on storage account"

echo "Uploading ${DIR} to static web storage"

az storage blob upload-batch \
    --account-name "${STORAGE_ACCOUNT}" \
    --auth-mode login \
    --destination '$web' \
    --source ${DIR} \
    --no-progress \
    --only-show-errors

echo "Removing network rule on storage account"
az storage account network-rule remove --account-name ${STORAGE_ACCOUNT} --ip-address ${IPADDR}
echo "Removed network rule on storage account"
