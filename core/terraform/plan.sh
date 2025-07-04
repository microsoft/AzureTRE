#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# shellcheck disable=SC1091
source "../../devops/scripts/kv_add_network_exception.sh"

# shellcheck disable=SC1091
source "../../devops/scripts/mgmtstorage_enable_public_access.sh"

TS=$(date +"%s")
PLAN_FILE="${TS}-tre-core.tfplan"
LOG_FILE="${TS}-tre-core.log"

# This variables are loaded in for us
# shellcheck disable=SC2154
../../devops/scripts/terraform_wrapper.sh \
  -g "${TF_VAR_mgmt_resource_group_name}" \
  -s "${TF_VAR_mgmt_storage_account_name}" \
  -n "${TF_VAR_terraform_state_container_name}" \
  -k "${TRE_ID}" \
  -l "${LOG_FILE}" \
  -c "terraform plan -out ${PLAN_FILE} && \
  terraform show ${PLAN_FILE}"
