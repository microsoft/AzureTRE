#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

if [ ! -f "$1" ]; then
  if [ -z "${USE_ENV_VARS_NOT_FILES:-}" ]; then
    echo -e "\e[31m»»» 💥 Unable to find $1 file, please create file and try again!\e[0m"
    #exit
  fi
else
  while read -r line
  do
    name=$(echo $line | cut -d= -f1)
    value=$(echo $line | cut -d= -f2)
    if [[ ("${value:0:1}" == "'" &&  "${value: -1:1}" == "'") || (("${value:0:1}" == "\"" &&  "${value: -1:1}" == "\"")) ]]; then
      value=${value:1:-1}
    fi
    declare -g $name="$value"
    export "${name?}"
  done < <(grep -v -e '^[[:space:]]*$' -e '^#' "$1" | sed 's/.*=/TF_VAR_\L&/') # feed in via Process Substition to avoid bash subshell (http://mywiki.wooledge.org/ProcessSubstitution)
fi

set +o nounset
