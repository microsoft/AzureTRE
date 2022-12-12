#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace
#
# Usage:
#    env_to_yaml_config.sh <.env file>
#

cp config.sample.yaml config.yaml
# Loop over the relevant lines in the file specified in $1 (passed in after the loop)
# The loop source filters the lines in the source file to those that should be treated
# as variable definitions

env_files=()

for p in "devops/auth.env" "devops/.env" "templates/core/.env"
do
  if [ -r "$p" ]
  then
    env_files+=("$p")
  else
    echo -e "\e[31m»»» ⚠️ Your $p file has not been setup! 😥 Make sure to fill in the missing configration in config.yaml."
  fi
done

for f in "${env_files[@]}"
do
  while read -r line
  do
    # split the line into name/value
    name=$(echo "$line" | cut -d= -f1| tr '[:upper:]' '[:lower:]')
    value=$(echo "$line" | cut -d= -f2)

    if [ "$f" == "devops/auth.env" ]; then
      yq e -i "(.authentication | .\"$name\") = $value" config.yaml
    else
      # if the value is quote-delimited then strip that as we quote in the declare statement
      if [[ ("${value:0:1}" == "'" &&  "${value: -1:1}" == "'") || (("${value:0:1}" == "\"" &&  "${value: -1:1}" == "\"")) ]]; then
        value=${value:1:-1}
      fi
      if [[ ($value == ?(-)+([0-9]) || $value == "true" ||  $value == "false")]]; then
        yq e -i "(.. | select(has(\"$name\")).\"$name\") = $value" config.yaml
      else
        # Set value in config.yaml file
        yq e -i "(.. | select(has(\"$name\")).\"$name\") = \"$value\"" config.yaml
      fi
    fi
  done < <(grep -v -e '^[[:space:]]*$' -e '^#' "$f" )
done


set +o nounset
