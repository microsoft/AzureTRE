#!/bin/bash

# This script register a bundle with the TRE API. It relies on the bundle
# pre-existing in the remote repository (i.e. has been publish beforehand).

set -o errexit
set -o pipefail
# set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -r, --acr-name        Azure Container Registry Name
        -t, --bundle-type     Bundle type, workspace or workspace_service
        -c, --current         Make this the currently deployed version of this template
        -i, --insecure        Bypass SSL certificate checks
        -u, --tre_url         URL for the TRE (required for automatic registration)
        -a, --access-token    Azure access token to automatically post to the API (required for automatic registration)
        -v, --verify          Verify registration with the API
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

current="false"
verify=false

while [ "$1" != "" ]; do
    case $1 in
    -u | --tre_url)
        shift
        tre_url=$1
        ;;
    -r | --acr-name)
        shift
        acr_name=$1
        ;;
    -t | --bundle-type)
        shift
        case $1 in
        workspace)
        ;;
        workspace_service)
        ;;
        user_resource)
        ;;
        *)
            echo "Bundle type must be workspace, workspace_service or user_resource, not $1"
            exit 1
        esac
        bundle_type=$1
        ;;
    -c| --current)
        current="true"
        ;;
    -i| --insecure)
        insecure=1
        ;;
    -a | --access-token)
        shift
        access_token=$1
        ;;
    -v| --verify)
        verify=true
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

explain_json=$(porter explain --reference ${acr_name}.azurecr.io/$(yq eval '.name' porter.yaml):v$(yq eval '.version' porter.yaml) -o json)

payload=$(echo ${explain_json} | jq --argfile json_schema template_schema.json --arg current "${current}" --arg bundle_type "${bundle_type}" '. + {"json_schema": $json_schema, "resourceType": $bundle_type, "current": $current}')

if [ -z "${access_token}" ]
then
  if [ ! -z "${RESOURCE}" ] && [ ! -z "${CLIENT_ID}" ] && [ ! -z "${USERNAME}" ] && [ ! -z "${PASSWORD}" ] && [ ! -z "${AUTH_TENANT_ID}" ]
  then
    # we didn't get an access token but we can generate one.
    echo "Using ENV credentials to generate access token..."
    access_token=$(curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d \
      "grant_type=password&resource=${RESOURCE}&client_id=${CLIENT_ID}&username=${USERNAME}&password=${PASSWORD}&scope=default)" \
      https://login.microsoftonline.com/${AUTH_TENANT_ID}/oauth2/token | jq -r '.access_token')
  fi
fi

if [ -z "${access_token}" ]
then
  echo "Use the following payload to register the template:"
  echo $(echo ${payload} | jq --color-output .)
else
  if [[ -n ${insecure+x} ]]; then
      options=" -k"
  fi

  case "${BUNDLE_TYPE}" in
    ("workspace") tre_get_path="api/workspace-templates" ;;
    ("workspace_service") tre_get_path="api/workspace-service-templates" ;;
  esac

  echo -e "Server Response:\n"
  eval "curl -X 'POST' ${tre_url}/${tre_get_path} -H 'accept: application/json' -H 'Content-Type: application/json' -H 'Authorization: Bearer ${access_token}' -d '${payload}' ${options}"
  echo -e "\n"

  if ((verify))
  then
    # Check that the template got registered
    template_name=$(yq eval '.name' porter.yaml)
    status_code=$(curl -X "GET" "${tre_url}/${tre_get_path}/${template_name}" -H "accept: application/json" -H "Authorization: Bearer ${access_token}" ${options} -s -w "%{http_code}" -o /dev/null)

    if [[ ${status_code} != 200 ]]
    then
      echo "::warning ::Template API check for ${bundle_type} ${template_name} returned http status: ${status_code}"
      exit 1
    fi
  fi
fi
