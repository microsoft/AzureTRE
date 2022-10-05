#!/bin/bash

set -o errexit
set -o pipefail


function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -p, --property                A name/value pair property in the format name=value
USAGE
    exit 1
}

while [ "$1" != "" ]; do
    case "$1" in
      --*)
        names+=("${1:2}")
        shift
        values+=("$1")
        ;;

    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next

done

# echo each of the names and values by index
for index in "${!names[@]}"; do
  name=${names[$index]}
  value=${values[$index]}

  echo "${name}:${value}"
done




