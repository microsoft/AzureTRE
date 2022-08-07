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
  # doesn't work with quotes
  # shellcheck disable=SC2046
  export $(grep -v -e '^[[:space:]]*$' -e '^#' "$1"  | sed 's/.*=/TF_VAR_\L&/' | xargs)
fi

set +o nounset
