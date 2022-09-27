#!/bin/bash
# not setting script options as we're sourcing this script
# so options set here end up affecting the caller's context

#
# Usage:
#    load_env.sh <.env file> [TERRAFORM]
#
# If TERRAFORM is specfied then env var names are converted to lower case and prefixed with TF_VAR_
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
    name=$(echo $line | cut -d= -f1)
    value=$(echo $line | cut -d= -f2)

    if [[ "$2" == "TERRAFORM" ]]; then
      # If TERRAFORM is specified the convert FOO=BAR to TF_VAR_foo=BAR
      name="TF_VAR_$(echo "$name" | tr '[:upper:]' '[:lower:]')"
    fi

    # if the value is quote-delimited then strip that as we quote in the declare statement
    if [[ ("${value:0:1}" == "'" &&  "${value: -1:1}" == "'") || (("${value:0:1}" == "\"" &&  "${value: -1:1}" == "\"")) ]]; then
      value=${value:1:-1}
    fi

    # declare the variable and export to the caller's context
    declare -g $name="$value"
    export "${name?}"
  done < <(grep -v -e '^[[:space:]]*$' -e '^#' "$1" ) # feed in via Process Substition to avoid bash subshell (http://mywiki.wooledge.org/ProcessSubstitution)
fi
