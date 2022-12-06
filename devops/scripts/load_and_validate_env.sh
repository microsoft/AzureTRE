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
    has_dupes=$(yq e '... comments=""|.. | select(. == "*") | {(path | .[-1]): .}| keys' config.yaml | uniq -d)
    if [ -n "${has_dupes:-}" ]; then
      echo -e "\e[31m»»» 💥 There are duplicate keys in your config, please fix and try again!\e[0m"
      exit
    fi

    # Validate config schema
    pajv validate -s config_schema.json -d config.yaml

    # declare the variable and export to the caller's context
    STRIP_COMMENTS="... comments=\"\""
    GET_LEAF_KEYS="... | select(. == \"*\") | {(path | .[-1]): .}"
    UPCASE_KEYS="with_entries(.key |= upcase)"
    TF_KEYS="with_entries(.key |= \"TF_VAR_\" + .)"
    FORMAT_FOR_ENV_EXPORT="to_entries| map(.key + \"=\" +  .value)|join(\" \")"

    # Export as UPPERCASE keys env vars
    # shellcheck disable=SC2046
    export $(yq e "$STRIP_COMMENTS|$GET_LEAF_KEYS|$UPCASE_KEYS| $FORMAT_FOR_ENV_EXPORT" config.yaml)
    # Export as Terraform keys env vars
    # shellcheck disable=SC2046
    export $(yq e "$STRIP_COMMENTS|$GET_LEAF_KEYS|$TF_KEYS| $FORMAT_FOR_ENV_EXPORT" config.yaml)
fi

set +o nounset
