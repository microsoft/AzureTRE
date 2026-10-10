#!/bin/bash
set -e

# This file is sourced inside Makefile && chains, where Bash ignores errexit.
# Check failures explicitly so callers cannot continue with missing outputs.
# shellcheck disable=SC1091
# shellcheck disable=SC2154
source ../../devops/scripts/storage_enable_public_access.sh \
  --storage-account-name "${TF_VAR_mgmt_storage_account_name}" \
  --resource-group-name "${TF_VAR_mgmt_resource_group_name}" || return $?

core_outputs_file=../tre_output.json
core_outputs_temporary=""
if [ ! -s "$core_outputs_file" ]; then
  # Connect to the remote backend of Terraform.
  export TF_LOG=""
  # shellcheck disable=SC2154
  terraform init -input=false -backend=true -reconfigure \
      -backend-config="resource_group_name=$TF_VAR_mgmt_resource_group_name" \
      -backend-config="storage_account_name=$TF_VAR_mgmt_storage_account_name" \
      -backend-config="container_name=$TF_VAR_terraform_state_container_name" \
      -backend-config="key=${TRE_ID}" || return $?

  # Keep Terraform output temporary until it has been validated and converted.
  core_outputs_temporary=$(mktemp ../tre_output.json.tmp.XXXXXX) || return $?
  if terraform output -json > "$core_outputs_temporary"; then
    core_outputs_file="$core_outputs_temporary"
  else
    core_outputs_exit=$?
    rm -f "$core_outputs_temporary"
    return "$core_outputs_exit"
  fi
fi

if ! jq -e 'type == "object" and length > 0' "$core_outputs_file" > /dev/null; then
  if [ -n "$core_outputs_temporary" ]; then rm -f "$core_outputs_temporary"; fi
  echo "Terraform outputs are empty or invalid. Check the state and regenerate core/tre_output.json." >&2
  return 1
fi

# Pull in the core template environment variables for the additional values.
if [ -f ../.env ]; then
  # shellcheck disable=SC1091
  source ../.env || {
    core_outputs_exit=$?
    if [ -n "$core_outputs_temporary" ]; then rm -f "$core_outputs_temporary"; fi
    return "$core_outputs_exit"
  }
fi

# Both environment readers require literal, single-line, single-quoted values.
# Bash variables cannot contain NUL bytes.
for core_env_variable in WORKSPACE_API_CLIENT_ID WORKSPACE_API_CLIENT_SECRET SUB_ID TENANT_ID; do
  case "${!core_env_variable}" in
    *"'"*|*$'\r'*|*$'\n'*)
      if [ -n "$core_outputs_temporary" ]; then rm -f "$core_outputs_temporary"; fi
      echo "${core_env_variable} contains a single quote or newline. Correct the value and regenerate core/private.env." >&2
      return 1
      ;;
  esac
done

# Preserve the previous environment file if conversion or writing fails.
core_env_temporary=$(mktemp ../private.env.tmp.XXXXXX) || {
  core_outputs_exit=$?
  if [ -n "$core_outputs_temporary" ]; then rm -f "$core_outputs_temporary"; fi
  return "$core_outputs_exit"
}
if ./json-to-env.sh < "$core_outputs_file" > "$core_env_temporary" && \
  printf "%s='%s'\n" \
    TEST_WORKSPACE_APP_ID "${WORKSPACE_API_CLIENT_ID}" \
    TEST_WORKSPACE_APP_SECRET "${WORKSPACE_API_CLIENT_SECRET}" \
    SUBSCRIPTION_ID "${SUB_ID}" \
    AZURE_SUBSCRIPTION_ID "${SUB_ID}" \
    AZURE_TENANT_ID "${TENANT_ID}" >> "$core_env_temporary"; then
  if [ -n "$core_outputs_temporary" ]; then
    mv "$core_outputs_temporary" ../tre_output.json || {
      core_outputs_exit=$?
      rm -f "$core_outputs_temporary" "$core_env_temporary"
      return "$core_outputs_exit"
    }
  fi
  mv "$core_env_temporary" ../private.env || {
    core_outputs_exit=$?
    rm -f "$core_env_temporary"
    return "$core_outputs_exit"
  }
else
  core_outputs_exit=$?
  if [ -n "$core_outputs_temporary" ]; then rm -f "$core_outputs_temporary"; fi
  rm -f "$core_env_temporary"
  return "$core_outputs_exit"
fi
