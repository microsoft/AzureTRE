#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# This is where we can migrate any Terraform before we plan and apply
# For instance deprecated Terraform resources
# shellcheck disable=SC1091
source ./migrate.sh

PLAN_FILE="tfplan$$"
TS=$(date +"%s")
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
  terraform apply -input=false -auto-approve ${PLAN_FILE} && \
  terraform output -json > ../tre_output.json"

./update_tags.sh
