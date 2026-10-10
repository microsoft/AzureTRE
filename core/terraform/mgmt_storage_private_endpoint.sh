#!/bin/bash
#
# Create the resource processor's management storage private endpoint before the main core apply.
#
# The management storage account also holds the Terraform state. Creating its private endpoint
# changes the storage account's public DNS alias chain, so state reads and writes during the same
# apply can fail with "no such host". This script creates the private endpoint in a short targeted
# apply, then verifies the new DNS alias and backend reads before the main apply starts.
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
  local expected_alias="${host%%.*}.privatelink.${host#*.}"
  local successes=0
  local attempt aliases answer backend_error

  echo "Waiting for ${expected_alias}, address resolution and backend access (${DNS_REQUIRED_SUCCESSES} consecutive checks)"
  for ((attempt=1; attempt<=DNS_MAX_ATTEMPTS; attempt++)); do
    aliases=$(dig +time=5 +tries=1 +short CNAME "${host}" 2>&1) || aliases=""
    if ! grep -ixFq "${expected_alias}." <<< "${aliases}"; then
      successes=0
      echo "$(timestamp) DNS attempt ${attempt}/${DNS_MAX_ATTEMPTS}: expected alias not observed: ${aliases:-no answer}"
    elif ! answer=$(timeout 15 getent ahosts "${host}" 2>&1) || [[ -z "${answer}" ]]; then
      successes=0
      echo "$(timestamp) DNS attempt ${attempt}/${DNS_MAX_ATTEMPTS}: ${host} did not resolve ${answer}"
    elif ! backend_error=$(timeout 30 terraform state pull 2>&1 >/dev/null); then
      successes=0
      echo "$(timestamp) DNS attempt ${attempt}/${DNS_MAX_ATTEMPTS}: backend read failed: ${backend_error}"
    else
      successes=$((successes + 1))
      echo "$(timestamp) DNS attempt ${attempt}/${DNS_MAX_ATTEMPTS}: alias, address and backend ready (${successes}/${DNS_REQUIRED_SUCCESSES})"
      echo "  CNAME: ${aliases}"
      echo "${answer}" | awk '{print "  " $0}'
      if [[ "${successes}" -ge "${DNS_REQUIRED_SUCCESSES}" ]]; then
        return 0
      fi
    fi
    if [[ "${attempt}" -lt "${DNS_MAX_ATTEMPTS}" ]]; then
      sleep "${DNS_INTERVAL_SECONDS}"
    fi
  done

  echo "Error: ${host} did not become ready after ${DNS_MAX_ATTEMPTS} attempts." >&2
  echo "Configured resolver diagnostics:"
  dig +time=2 +tries=1 +noall +answer +comments +stats "${host}" A || true
  echo "Azure resolver diagnostics (168.63.129.16):"
  dig @168.63.129.16 +time=2 +tries=1 +noall +answer +comments +stats "${host}" A || true
  echo "The main apply has not started. Inspect DNS and backend access, then re-run to repeat these checks." >&2
  return 1
}

if [[ "${TF_VAR_resource_processor_type:-vmss_porter}" != "vmss_porter" ]]; then
  echo "Resource processor type is not vmss_porter; skipping management storage private endpoint step"
  exit 0
fi

for required_command in dig getent timeout; do
  if ! command -v "${required_command}" >/dev/null; then
    echo "Error: ${required_command} is required. Rebuild the repository development container." >&2
    exit 1
  fi
done

host=$(state_blob_host)
state_addresses=$(terraform state list)
if grep -qxF "${PE_ADDRESS}" <<< "${state_addresses}"; then
  echo "Management storage private endpoint already in state; skipping targeted apply"
else
  echo "$(timestamp) Creating management storage private endpoint before the main core apply"
  timeout 15 getent ahosts "${host}" | awk '{print "  before: " $0}' || echo "  before: ${host} did not resolve"

  PE_PLAN_FILE="$(date +"%s")-tre-core-mgmt-pe.tfplan"
  terraform plan -input=false -target="${PE_ADDRESS}" -out "${PE_PLAN_FILE}"
  terraform apply -input=false -auto-approve "${PE_PLAN_FILE}"
  echo "$(timestamp) Management storage private endpoint apply finished"
fi

wait_for_stable_dns "${host}"
