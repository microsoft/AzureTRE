#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace
#
# Usage:
#    load_env.sh <.env file>
#

cp config.sample.yaml config.yaml
# Loop over the relevant lines in the file specified in $1 (passed in after the loop)
# The loop source filters the lines in the source file to those that should be treated
# as variable definitions
for f in "devops/auth.env" "devops/.env" "templates/core/.env"
do
  while read -r line
  do
    # split the line into name/value
    name=$(echo "$line" | cut -d= -f1| tr '[:upper:]' '[:lower:]')
    value=$(echo "$line" | cut -d= -f2)

    # if the value is quote-delimited then strip that as we quote in the declare statement
    if [[ ("${value:0:1}" == "'" &&  "${value: -1:1}" == "'") || (("${value:0:1}" == "\"" &&  "${value: -1:1}" == "\"")) ]]; then
      value=${value:1:-1}
    fi

    # Set value in config.yaml file
    yq e -i "(.[] | select(has(\"$name\")).\"$name\") = \"$value\"" config.yaml
  done < <(grep -v -e '^[[:space:]]*$' -e '^#' "$f" )
done


set +o nounset
