#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# These variables are loaded in for us
# shellcheck disable=SC2154
../../devops/scripts/terraform_wrapper.sh -g "${TF_VAR_mgmt_resource_group_name}" \
                                          -s "${TF_VAR_mgmt_storage_account_name}" \
                                          -n "${TF_VAR_terraform_state_container_name}" \
                                          -k "${TRE_ID}" -c "terraform destroy -auto-approve"
