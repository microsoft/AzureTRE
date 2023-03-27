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

    # Get any default entries from config schema and export. Any values in config.yaml will override these defaults
    DEFAULT_VALUES=$(yq '[... |select(has("default"))| {"":path | .[-1] | upcase , " ": .default }| to_entries| map("=" +  .value)|join("")  ]'  config_schema.json)
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

    AZURE_ENVIRONMENT=$(az cloud show --query name --output tsv)
    export AZURE_ENVIRONMENT

    declare -A cloudapp_endpoint_suffix=( ["public"]="cloudapp.azure.com" ["usgovernment"]="cloudapp.usgovcloudapi.net")
    export TRE_URL=${TRE_URL:-https://${TRE_ID}.${LOCATION}.${cloudapp_endpoint_suffix[${ARM_ENVIRONMENT}]}}
fi

set +o nounset
