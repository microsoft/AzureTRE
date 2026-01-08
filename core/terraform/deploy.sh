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

# This is where we can migrate any Terraform before we plan and apply
# For instance deprecated Terraform resources
# shellcheck disable=SC1091
source ./migrate.sh

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
  # Note: Terraform parallelism is increased from the default (10) to 25 to speed up
  # core infrastructure deployments, which provision many resources. This may increase
  # the risk of hitting Azure API rate limits and can make error diagnosis harder.
  # If deployment reliability issues arise (e.g., frequent throttling), consider
  # lowering the parallelism value.
  -c "terraform plan --parallelism=25 -out ${PLAN_FILE} && \
  terraform apply -input=false -auto-approve --parallelism=25 ${PLAN_FILE} && \
  terraform output -json > ../tre_output.json"

./update_tags.sh
