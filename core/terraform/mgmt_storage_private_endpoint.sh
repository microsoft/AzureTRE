#!/bin/bash
#
# Create the resource processor's management storage private endpoint before the main core apply.
#
# The management storage account also holds the Terraform state. Creating its private endpoint
# changes the storage account's public DNS alias chain, so state reads and writes during the same
# apply can fail with "no such host". This script creates the private endpoint in a short targeted
# apply, then waits for the state endpoint to resolve consistently before the main apply starts.
#
# Run from core/terraform after "terraform init".
#

set -o errexit
set -o pipefail
set -o nounset

PE_ADDRESS='module.resource_processor_vmss_porter[0].azurerm_private_endpoint.mgmtblobpe'
DNS_REQUIRED_SUCCESSES="${MGMT_STORAGE_DNS_REQUIRED_SUCCESSES:-3}"
DNS_MAX_ATTEMPTS="${MGMT_STORAGE_DNS_MAX_ATTEMPTS:-30}"
DNS_INTERVAL_SECONDS="${MGMT_STORAGE_DNS_INTERVAL_SECONDS:-10}"

function timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

function state_blob_host() {
  local endpoint
  # shellcheck disable=SC2154
  endpoint=$(az storage account show \
    --name "${TF_VAR_mgmt_storage_account_name}" \
    --resource-group "${TF_VAR_mgmt_resource_group_name}" \
    --query primaryEndpoints.blob --output tsv)
  endpoint="${endpoint#https://}"
  echo "${endpoint%%/*}"
}

function wait_for_stable_dns() {
  local host="$1"
  local successes=0
  local attempt answer

  echo "Waiting for ${host} to resolve ${DNS_REQUIRED_SUCCESSES} consecutive times"
  for ((attempt=1; attempt<=DNS_MAX_ATTEMPTS; attempt++)); do
    if answer=$(getent ahosts "${host}" 2>&1) && [[ -n "${answer}" ]]; then
      successes=$((successes + 1))
      echo "$(timestamp) DNS attempt ${attempt}/${DNS_MAX_ATTEMPTS}: resolved (${successes}/${DNS_REQUIRED_SUCCESSES})"
      echo "${answer}" | awk '{print "  " $0}'
      if [[ "${successes}" -ge "${DNS_REQUIRED_SUCCESSES}" ]]; then
        return 0
      fi
    else
      successes=0
      echo "$(timestamp) DNS attempt ${attempt}/${DNS_MAX_ATTEMPTS}: ${host} did not resolve ${answer}"
    fi
    if [[ "${attempt}" -lt "${DNS_MAX_ATTEMPTS}" ]]; then
      sleep "${DNS_INTERVAL_SECONDS}"
    fi
  done

  echo "Error: ${host} did not resolve consistently after ${DNS_MAX_ATTEMPTS} attempts." >&2
  echo "The private endpoint is in Terraform state. Re-run the deployment once DNS resolves." >&2
  return 1
}

if [[ "${TF_VAR_resource_processor_type:-vmss_porter}" != "vmss_porter" ]]; then
  echo "Resource processor type is not vmss_porter; skipping management storage private endpoint step"
  exit 0
fi

state_addresses=$(terraform state list)
if grep -qxF "${PE_ADDRESS}" <<< "${state_addresses}"; then
  echo "Management storage private endpoint already in state; skipping targeted apply"
  exit 0
fi

host=$(state_blob_host)
echo "$(timestamp) Creating management storage private endpoint before the main core apply"
getent ahosts "${host}" | awk '{print "  before: " $0}' || echo "  before: ${host} did not resolve"

PE_PLAN_FILE="$(date +"%s")-tre-core-mgmt-pe.tfplan"
terraform plan -input=false -target="${PE_ADDRESS}" -out "${PE_PLAN_FILE}"
terraform apply -input=false -auto-approve "${PE_PLAN_FILE}"
echo "$(timestamp) Management storage private endpoint apply finished"

wait_for_stable_dns "${host}"
