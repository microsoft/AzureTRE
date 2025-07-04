#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# shellcheck disable=SC1091
source "../../devops/scripts/kv_add_network_exception.sh"

# shellcheck disable=SC1091
# shellcheck disable=SC2154
source "../../devops/scripts/storage_enable_public_access.sh" \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}"

TS=$(date +"%s")
PLAN_FILE="${TS}-tre-core.tfplan"
LOG_FILE="${TS}-tre-core.log"

# This variables are loaded in for us
# shellcheck disable=SC2154
../../devops/scripts/terraform_wrapper.sh \
  -d "${PWD}" \
  -g "${TF_VAR_mgmt_resource_group_name}" \
  -s "${TF_VAR_mgmt_storage_account_name}" \
  -n "${TF_VAR_terraform_state_container_name}" \
  -k "${TRE_ID}" \
  -l "${LOG_FILE}" \
  -c "terraform plan -out ${PLAN_FILE} && \
  terraform show ${PLAN_FILE}"
