#!/bin/bash

# This script migrates the Cosmos database based on any breaking changes that have occurred.
# Cosmos is behind a private network, so we call the /migrations endpoint of the API

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -u, --tre_url                 URL for the TRE
        -a, --access-token            Azure access token to automatically post to the API
        -i, --insecure                Bypass SSL certificate checks
USAGE
    exit 1
}

function get_http_code() {
  curl_output="$1"
  http_code=$(echo "${curl_output}" | grep HTTP | sed 's/.*HTTP\/1\.1 \([0-9]\+\).*/\1/' | tail -n 1)
}

curl_options=(--retry 3 --retry-max-time 300 --max-time 90)

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -u | --tre_url)
        shift
        tre_url=$1
        ;;
    -a | --access-token)
        shift
        access_token=$1
        ;;
    -i| --insecure)
        curl_options+=("-k")
        ;;
    *)
        echo "Unexpected argument: '$1'"
        usage
        ;;
    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next
done

# done with processing args and can set this
set -o nounset

if [[ -z ${tre_url:-} ]]; then
    echo -e "No TRE URI provided.\n"
    usage
fi

if [ -z "${access_token:-}" ]; then
  # If access token isn't set, try to obtain it
  if [ -z "${ACCESS_TOKEN:-}" ]
  then
    echo "API access token isn't available - migrating state store not possible. "
    exit 1
  fi
  access_token=${ACCESS_TOKEN}
fi

migrate_result=$(curl -i -X "POST" "${tre_url}/api/migrations" "${curl_options[@]}" \
                -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer ${access_token}")
get_http_code "${migrate_result}"
echo "${migrate_result}"
if [[ ${http_code} != 202 ]]; then
  echo "Error while migrating state store"
  exit 1
fi
