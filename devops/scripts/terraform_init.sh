#!/bin/bash

# Source this helper before initialising a management Terraform backend.
# Only recognised workspace-listing permission failures are safe to retry.

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
