#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace
#
# Usage:
#    load_and_validate_env.sh
#

# shellcheck disable=SC1091
source "${DIR}"/construct_tre_url.sh
# shellcheck disable=SC1091
source "${DIR}"/convert_azure_env_to_arm_env.sh

if [ ! -f "config.yaml" ]; then
  if [ -z "${USE_ENV_VARS_NOT_FILES:-}" ]; then
    echo -e "\e[31m»»» 💥 Unable to find config.yaml file, please create file and try again!\e[0m"
    #exit
  fi
else
    # Validate no duplicate keys in config
    has_dupes=$(yq e '.. | select(. == "*") | {(path | .[-1]): .}| keys' config.yaml | sort| uniq -d)
    if [ -n "${has_dupes:-}" ]; then
      echo -e "\e[31m»»» 💥 There are duplicate keys in your config, please fix and try again!\e[0m"
      exit 1
    fi

    # Validate config schema
    if [[ $(pajv validate -s "$DIR/../../config_schema.json" -d config.yaml) != *valid* ]]; then
      echo -e "\e[31m»»» ⚠️ Your config.yaml is invalid 😥 Please fix the errors and retry."
      exit 1
    fi

    # Get any default entries from config schema and export. Any values in config.yaml will override these defaults
    DEFAULT_VALUES=$(yq '[... |select(has("default"))| {"":path | .[-1] | upcase , " ": .default }| to_entries| map("=" +  .value)|join("")  ]' --output-format=yaml "$DIR/../../config_schema.json")

    # Format env string
    DEFAULT_VALUES=${DEFAULT_VALUES//"- ="}

    # Catch if no default values have been declared
    if [ ${#DEFAULT_VALUES} -gt 2 ]; then

    # Export default values
      for item in $DEFAULT_VALUES
      do
        # Export as UPPERCASE keys env vars
        # shellcheck disable=SC2163
        export "$item"
        # TF_VAR requires the key in lowercase
        IFS='=' read -ra arr <<< "$item"
        tfkey=$(echo "${arr[0]}" | tr '[:upper:]' '[:lower:]')
        tfvar="TF_VAR_$tfkey=${arr[1]}"
        # shellcheck disable=SC2163
        export "$tfvar"
      done
    fi

    # yq query to get all leaf keys, converting any arrays to a single line json array.
    GET_LEAF_KEYS="with(.. | select(kind == \"seq\"); . = @json) | .. | select(kind == \"scalar\") | ... comments=\"\""
    # Map keys to uppercase yq query
    UPCASE_KEYS="{key | upcase: .}"
    # Prefix keys with TF_VAR_ yq query
    TF_KEYS="{\"TF_VAR_\" + key: .}"
    # Yq query to format the output to be in form: key=value
    FORMAT_FOR_ENV_EXPORT="to_entries| map(.key + \"=\" +  .value)|join(\" \")"

    # Export as UPPERCASE keys env vars
    # (process line by line to preserve values with spaces in)
    while IFS= read -r KV; do
      # shellcheck disable=SC2163
      export "$KV"
    done <<< "$(yq e "$GET_LEAF_KEYS|$UPCASE_KEYS| $FORMAT_FOR_ENV_EXPORT" config.yaml)"

    # Export as Terraform keys env vars
    # (process line by line to preserve values with spaces in)
    while IFS= read -r KV; do
      # shellcheck disable=SC2163
      export "$KV"
    done <<< "$(yq e "$GET_LEAF_KEYS|$TF_KEYS| $FORMAT_FOR_ENV_EXPORT" config.yaml)"

    # Source AZURE_ENVIRONMENT and setup the ARM_ENVIRONMENT based on it
    AZURE_ENVIRONMENT=$(az cloud show --query name --output tsv)
    export AZURE_ENVIRONMENT

    # The ARM Environment is required by terraform to indicate the destination cloud.
    ARM_ENVIRONMENT=$(convert_azure_env_to_arm_env "${AZURE_ENVIRONMENT}")
    export ARM_ENVIRONMENT
    export TF_VAR_arm_environment="${ARM_ENVIRONMENT}"

    TRE_URL=$(construct_tre_url "${TRE_ID}" "${LOCATION}" "${AZURE_ENVIRONMENT}")
    export TRE_URL
fi

# if local debugging is configured, then set vars required by ~/.porter/config.yaml
if [ -f "$DIR/../../core/private.env" ]; then
  # shellcheck disable=SC1091
  source "$DIR/../../core/private.env"
  # shellcheck disable=SC2153
  KEY_VAULT_URL=$KEYVAULT_URI
  export KEY_VAULT_URL
fi

set +o nounset
