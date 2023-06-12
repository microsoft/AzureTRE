#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PLAN_FILE="tfplan$$"
TS=$(date +"%s")
LOG_FILE="${TS}-tre-compute-gallery.log"

# shellcheck disable=SC2154
"$SCRIPT_DIR"/../../devops/scripts/terraform_wrapper.sh \
  -g "${TF_VAR_mgmt_resource_group_name}" \
  -s "${TF_VAR_mgmt_storage_account_name}" \
  -n "${TF_VAR_terraform_state_container_name}" \
  -k "computegallery${TRE_ID}" \
  -l "${LOG_FILE}" \
  -c "terraform plan -out ${PLAN_FILE} && \
  terraform apply -input=false -auto-approve ${PLAN_FILE} && \
  terraform output -json > ../tre_output.json"
