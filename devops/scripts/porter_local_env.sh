#!/bin/bash

# This script adds missing env vars that are needed to run porter commands locally.
# If a bundle defines a parameter that isn't in the environment it will be added.
# When/if this issue will be address, we could remove the script:
# https://github.com/getporter/porter/issues/2474

set -o errexit
set -o pipefail
# set -o xtrace

while read -r env_var_name; do
  if [[ -z "${!env_var_name}" ]]; then
    echo "${env_var_name} doesn't exist."
    # shellcheck disable=SC2086
    declare -g $env_var_name=
    export "${env_var_name?}"
  fi
done < <(jq -r '.parameters[].source.env' parameters.json)
