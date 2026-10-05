#!/bin/bash

# Source this helper before initialising a management Terraform backend.
# Retry recognised probe permissions and workspace-listing failures before state locking.

retry_with_backoff() {
  local func="$1"
  local sleep_time
  local status

  for sleep_time in 10 20 40 80 160; do
    if "$func"; then
      return 0
    else
      status=$?
    fi
    # A status of 1 is retryable. Other failures must retain their diagnostics.
    if [ "$status" -ne 1 ]; then
      return "$status"
    fi
    echo "Retrying ${func} in ${sleep_time} seconds..." >&2
    sleep "$sleep_time"
  done
  "$func"
}

is_storage_permission_error() {
  # Azure CLI can replace storage error codes with these messages before printing them.
  grep -Eq 'AuthorizationPermissionMismatch|AuthorizationFailure|(^|[^[:alnum:]])403([^[:alnum:]]|$)' <<< "$1" \
    || grep -Fq \
      -e 'You do not have the required permissions needed to perform this operation.' \
      -e 'The request may be blocked by network rules of storage account.' <<< "$1"
}

# Probe permissions on a separate blob before Terraform can acquire a state lease.
# The subshell keeps probe cleanup separate from the caller's network-access trap.
# Nested cleanup functions are invoked indirectly through retry_with_backoff and trap.
# shellcheck disable=SC2329
check_blob_access() (
  local probe_file probe_name probe_lease_id
  local probe_created=false
  local probe_lease_attempted=false

  probe_command() {
    local operation="$1"
    local output
    shift
    # shellcheck disable=SC2154
    if output=$(az storage blob "$@" \
      --account-name "$TF_VAR_mgmt_storage_account_name" \
      --container-name "$TF_VAR_terraform_state_container_name" \
      --auth-mode login --only-show-errors --output none 2>&1); then
      return 0
    fi

    # A finite probe lease can expire while permissions propagate. Only these
    # specific responses confirm that cleanup has already completed.
    if ! is_storage_permission_error "$output"; then
      if [[ "$operation" == release ]] && grep -Fq 'LeaseNotPresentWithLeaseOperation' <<< "$output"; then
        return 0
      fi
      if [[ "$operation" == delete ]] && grep -Fq 'BlobNotFound' <<< "$output"; then
        return 0
      fi
    fi
    printf 'ERROR: Blob readiness %s failed.\n%s\n' "$operation" "$output" >&2
    if is_storage_permission_error "$output"; then
      return 1
    fi
    return 2
  }

  release_probe_lease() {
    probe_command release lease release --blob-name "$probe_name" --lease-id "$probe_lease_id"
  }

  delete_probe_blob() {
    probe_command delete delete --name "$probe_name"
  }

  cleanup_probe() {
    local status=$?
    if [[ "$probe_created" == true ]]; then
      # The proposed ID is known even if acquisition returned an ambiguous error.
      # Never break a lease or release any lease on a Terraform state blob.
      if [[ "$probe_lease_attempted" == true ]]; then
        if retry_with_backoff release_probe_lease; then
          probe_lease_attempted=false
        else
          echo "ERROR: Could not confirm release of the finite lease on probe '$probe_name'." >&2
          status=2
        fi
      fi
      if [[ "$probe_lease_attempted" == false ]]; then
        if ! retry_with_backoff delete_probe_blob; then
          echo "ERROR: Could not clean up readiness probe '$probe_name'." >&2
          status=2
        fi
      fi
    fi
    rm -f "$probe_file"
    exit "$status"
  }

  probe_command list list --prefix bootstrap.tfstate --num-results 1 || return $?
  probe_file=$(mktemp "${TMPDIR:-/tmp}/azuretre-readiness.XXXXXXXX") || return 2
  trap cleanup_probe EXIT
  probe_lease_id=$(python3 -c 'import uuid; print(uuid.uuid4())') || return 2
  probe_name="azuretre-readiness-${probe_lease_id}"

  # Conditional creation prevents overwriting or deleting an existing blob.
  probe_command upload upload --name "$probe_name" --file "$probe_file" \
    --type block --overwrite false --if-none-match '*' --no-progress || return $?
  probe_created=true
  probe_lease_attempted=true
  probe_command acquire lease acquire --blob-name "$probe_name" \
    --lease-duration 60 --proposed-lease-id "$probe_lease_id" || return $?
  probe_command read show --name "$probe_name" --lease-id "$probe_lease_id" || return $?
  probe_command metadata metadata update --name "$probe_name" \
    --lease-id "$probe_lease_id" --metadata "readiness_probe=$probe_lease_id" || return $?
)

init_terraform() {
  local terraform_output
  local status
  if terraform_output=$(terraform init -input=false -backend=true -reconfigure -no-color 2>&1); then
    printf '%s\n' "$terraform_output"
    return 0
  else
    status=$?
  fi

  printf 'ERROR: terraform init failed (exit %s).\n%s\n' "$status" "$terraform_output" >&2
  # An unlock failure can also contain a 403. Never hide it or retry it as role propagation.
  if grep -Eiq 'Error (acquiring|releasing|locking|unlocking)|failed to (lock|unlock)|state blob is already locked|Lock Info:|Lock ID:' <<< "$terraform_output"; then
    echo "ERROR: Check the reported lock owner before attempting state recovery. No lock has been released by this helper." >&2
    return 2
  fi
  # Retry only workspace-listing permission failures, not unknown state errors.
  if grep -Fq 'Failed to get existing workspaces' <<< "$terraform_output" \
    && is_storage_permission_error "$terraform_output"; then
    return 1
  fi
  return 2
}
