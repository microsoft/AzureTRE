#!/bin/bash

# This script is called by a bundle to interact with the TRE API

function usage() {
    cat <<USAGE

    Usage: $0 [--tre_url]

    Options:
        --auth-tenant-id            The tenant that we are using to authenticate against
        --api-app-id                The application id, or the scope of the request
        --api-admin-client-id       The client id of an application/user that is authorised to use the API
        --api-admin-client-secret   The client secret of an application/user that is authorised to use the API
        --tre-url                   URL for the TRE (required for automatic registration)
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    --tre-url)
        shift
        tre_url=$1
        ;;
    --auth-tenant-id)
        shift
        auth_tenant_id=$1
        ;;
    --api-app-id)
        shift
        api_app_id=$1
        ;;
    --api-admin-client-id)
        shift
        api_admin_client_id=$1
        ;;
    --api-admin-client-secret)
        shift
        api_admin_client_secret=$1
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
    echo -e "No TRE url provided.\n"
    usage
fi

token_response=$(curl -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  https://login.microsoftonline.com/${auth_tenant_id}/oauth2/v2.0/token \
  -d "grant_type=client_credentials"   \
  -d "scope=api://${api_app_id}/.default"   \
  -d "client_id=${api_admin_client_id}"   \
  -d "client_secret=${api_admin_client_secret}")

if [ ! -z "${token_response:-}" ]; then
  access_token=$(echo ${token_response} | jq -r .access_token)
  if [[ ${access_token} == "null" ]]; then
      echo "Failed to obtain auth token for API:"
      echo ${token_response}
      exit 2
  fi
fi

tre_get_path="api/workspaces"
response=$(curl -X "GET" "${tre_url}/${tre_get_path}" \
  -H "accept: application/json" \
  -H "Authorization: Bearer ${access_token}")
echo $response
