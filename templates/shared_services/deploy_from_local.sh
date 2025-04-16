#!/bin/bash

# This script exists to support the migration from the firewall into a shared service bundle, that can be deployed from a dev workstation.

set -e

PLAN_FILE="tfplan$$"
TS=$(date +"%s")
LOG_FILE="${TS}-tre-${SHARED_SERVICE_KEY}.log"

LOC="$(dirname -- "$(readlink -f "${BASH_SOURCE}")")"

${LOC}/../../devops/scripts/terraform_wrapper.sh \
  -g $TF_VAR_mgmt_resource_group_name \
  -s $TF_VAR_mgmt_storage_account_name \
  -n $TF_VAR_terraform_state_container_name \
  -k ${TRE_ID}-${SHARED_SERVICE_KEY} \
  -l ${LOG_FILE} \
  -c "terraform plan -out ${PLAN_FILE} && \
  terraform apply -input=false -auto-approve ${PLAN_FILE} && \
  terraform output -json > ../tre_output.json"

