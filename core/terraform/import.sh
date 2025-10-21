#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

export TF_LOG=""

# This variables are loaded in for us
# shellcheck disable=SC2154
../../devops/scripts/terraform_wrapper.sh \
  -g "${TF_VAR_mgmt_resource_group_name}" \
  -s "${TF_VAR_mgmt_storage_account_name}" \
  -n "${TF_VAR_terraform_state_container_name}" \
  -k "${TRE_ID}" \
  -c "terraform import azurerm_key_vault_access_policy.deployer \"/subscriptions/23f86cef-93b3-45f3-858f-b11aa9a60201/resourceGroups/rg-cprddev/providers/Microsoft.KeyVault/vaults/kv-cprddev/objectId/a2661996-9af0-4acb-a528-0ce72040bea2\""
