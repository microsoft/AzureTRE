#!/bin/bash
# not setting script options as we're sourcing this script
# so options set here end up affecting the caller's context

if [ ! -f "$1" ]; then
  if [ -z "${USE_ENV_VARS_NOT_FILES:-}" ]; then
    echo -e "\e[31m»»» 💥 Unable to find $1 file, please create file and try again!\e[0m"
    #exit
  fi
else
  # Loop over the relevant lines in the file specified in $1 (passed in after the loop)
  # The loop source filters the lines in the source file to those that should be treated
  # as variable definitions. Additionally, names are lower-cased and prefixed with TF_VAR_
  while read -r line
  do
    # split the line into name/value
    name=$(echo $line | cut -d= -f1)
    value=$(echo $line | cut -d= -f2)
    # if the value is quote-delimited then strip that as we quote in the declare statement
    if [[ ("${value:0:1}" == "'" &&  "${value: -1:1}" == "'") || (("${value:0:1}" == "\"" &&  "${value: -1:1}" == "\"")) ]]; then
      value=${value:1:-1}
    fi
    # declare the variable and export to the caller's context
    declare -g $name="$value"
    export "${name?}"
  done < <(grep -v -e '^[[:space:]]*$' -e '^#' "$1" | sed 's/.*=/TF_VAR_\L&/') # feed in via Process Substition to avoid bash subshell (http://mywiki.wooledge.org/ProcessSubstitution)
fi

