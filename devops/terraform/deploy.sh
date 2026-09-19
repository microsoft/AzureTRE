#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# shellcheck disable=SC1091
source ../scripts/terraform_init.sh

# shellcheck disable=SC1091
# shellcheck disable=SC2154
source ../scripts/storage_enable_public_access.sh \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}"

PLAN_FILE="devops.tfplan"

if ! retry_with_backoff init_terraform; then
  echo "ERROR: Terraform backend initialisation failed. See the error above." >&2
  exit 1
fi
terraform plan -out ${PLAN_FILE}
terraform apply -auto-approve ${PLAN_FILE}

./update_tags.sh
