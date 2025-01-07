#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# add trap to remove deployment network exceptions
# shellcheck disable=SC1091
trap 'source "../../devops/scripts/remove_deployment_network_exceptions.sh"' EXIT

# now add deployment network exceptions
# shellcheck disable=SC1091
source "../../devops/scripts/add_deployment_network_exceptions.sh"

# These variables are loaded in for us
# shellcheck disable=SC2154
../../devops/scripts/terraform_wrapper.sh -g "${TF_VAR_mgmt_resource_group_name}" \
                                          -s "${TF_VAR_mgmt_storage_account_name}" \
                                          -n "${TF_VAR_terraform_state_container_name}" \
                                          -k "${TRE_ID}" -c "terraform destroy -auto-approve"
