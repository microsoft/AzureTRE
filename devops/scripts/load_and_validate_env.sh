#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace
#
# Usage:
#    load_and_validate_env.sh
#

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

    # Get leaf keys yq query
    GET_LEAF_KEYS=".. | select(. == \"*\") | {(path | .[-1]): .}"
    # Map keys to uppercase yq query
    UPCASE_KEYS="with_entries(.key |= upcase)"
    # Prefix keys with TF_VAR_ yq query
    TF_KEYS="with_entries(.key |= \"TF_VAR_\" + .)"
    # Yq query to format the output to be in form: key=value
    FORMAT_FOR_ENV_EXPORT="to_entries| map(.key + \"=\" +  .value)|join(\" \")"

    # Export as UPPERCASE keys env vars
    # shellcheck disable=SC2046
    export $(yq e "$GET_LEAF_KEYS|$UPCASE_KEYS| $FORMAT_FOR_ENV_EXPORT" config.yaml)
    # Export as Terraform keys env vars
    # shellcheck disable=SC2046
    export $(yq e "$GET_LEAF_KEYS|$TF_KEYS| $FORMAT_FOR_ENV_EXPORT" config.yaml)

    # Source AZURE_ENVIRONMENT and setup the  ARM_ENVIRONMENT based on it
    AZURE_ENVIRONMENT=$(az cloud show --query name --output tsv)
    export AZURE_ENVIRONMENT

    declare -A arm_environments=( ["AzureCloud"]="public" ["AzureUSGovernment"]="usgovernment")
    declare -A cloudapp_endpoint_suffix=( ["AzureCloud"]="cloudapp.azure.com" ["AzureUSGovernment"]="cloudapp.usgovcloudapi.net")

    # The ARM Environment is required by terrafform to indicate the destination cloud.
    export ARM_ENVIRONMENT="${arm_environments[${AZURE_ENVIRONMENT}]}"
    export TF_VAR_arm_environment="${arm_environments[${AZURE_ENVIRONMENT}]}"

    export TRE_URL=${TRE_URL:-https://${TRE_ID}.${LOCATION}.${cloudapp_endpoint_suffix[${AZURE_ENVIRONMENT}]}}
fi

set +o nounset
