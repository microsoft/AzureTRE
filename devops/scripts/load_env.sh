#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace
#
# Usage:
#    load_env.sh <.env file>
#

if [ ! -f "$1" ]; then
  if [ -z "${USE_ENV_VARS_NOT_FILES:-}" ]; then
    echo -e "\e[31m»»» 💥 Unable to find $1 file, please create file and try again!\e[0m"
    #exit
  fi
else
  # Loop over the relevant lines in the file specified in $1 (passed in after the loop)
  # The loop source filters the lines in the source file to those that should be treated
  # as variable definitions
  while read -r line
  do
    # split the line into name/value
    IFS='=' read -r name value <<< "$line"

    # Create the Terraform var name form, i.e. convert FOO=BAR to TF_VAR_foo=BAR
    tf_name="TF_VAR_$(echo "$name" | tr '[:upper:]' '[:lower:]')"

    # if the value is quote-delimited then strip that as we quote in the declare statement
    if [[ ("${value:0:1}" == "'" &&  "${value: -1:1}" == "'") || (("${value:0:1}" == "\"" &&  "${value: -1:1}" == "\"")) ]]; then
      value=${value:1:-1}
    fi

    # declare the variable and export to the caller's context
    # shellcheck disable=SC2086
    declare -g $name="$value"
    export "${name?}"
    # shellcheck disable=SC2086
    declare -g $tf_name="$value"
    export "${tf_name?}"
  done < <(grep -v -e '^[[:space:]]*$' -e '^#' "$1" ) # feed in via Process Substition to avoid bash subshell (http://mywiki.wooledge.org/ProcessSubstitution)
fi


set +o nounset
