#!/bin/bash

# This script register a bundle with the TRE API. It relies on the bundle
# pre-existing in the remote repository (i.e. has been publish beforehand).

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -r, --acr-name                Azure Container Registry Name
        -t, --bundle-type             Bundle type: workspace, workspace_service, user_resource or shared_service
        -w, --workspace-service-name  The template name of the user resource (if registering a user_resource)
        -c, --current                 Make this the currently deployed version of this template
        -i, --insecure                Bypass SSL certificate checks
        -u, --tre_url                 URL for the TRE (required for automatic registration)
        -a, --access-token            Azure access token to automatically post to the API (required for automatic registration)
        -v, --verify                  Verify registration with the API
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

current="false"
verify="false"

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
        shared_service)
        ;;
        *)
            echo "Bundle type must be workspace, workspace_service, shared_service or user_resource, not $1"
            exit 1
        esac
        bundle_type=$1
        ;;
    -w | --workspace-service-name)
        shift
        workspace_service_name=$1
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
        verify="true"
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

if [[ -z ${acr_name:-} ]]; then
    echo -e "No Azure Container Registry name provided\n"
    usage
fi

if [[ -z ${bundle_type:-} ]]; then
    echo -e "No bundle type provided\n"
    usage
fi

explain_json=$(porter explain --reference "${acr_name}".azurecr.io/"$(yq eval '.name' porter.yaml)":v"$(yq eval '.version' porter.yaml)" -o json)

payload=$(echo "${explain_json}" | jq --argfile json_schema template_schema.json --arg current "${current}" --arg bundle_type "${bundle_type}" '. + {"json_schema": $json_schema, "resourceType": $bundle_type, "current": $current}')

function get_http_code() {
  curl_output="$1"
  http_code=$(echo "${curl_output}" | grep HTTP | sed 's/.*HTTP\/1\.1 \([0-9]\+\).*/\1/' | tail -n 1)
}

if [ -z "${access_token:-}" ]; then
  # If access token isn't set, try to obtain it
  if [ -z "${ACCESS_TOKEN:-}" ]
  then
    echo "API access token isn't available - automatic bundle registration not possible. Use the script output to self-register. "
    echo "See documentation for more details: https://microsoft.github.io/AzureTRE/tre-admins/registering-templates/"
    echo "${payload}" | jq --color-output .
    exit 1
  fi
  access_token=${ACCESS_TOKEN}
fi
if [ "${bundle_type}" == "user_resource" ] && [ -z "${workspace_service_name:-}" ]; then
  echo -e "You must supply a workspace service_name name if you would like to automatically register the user_resource bundle\n"
  echo "${payload}" | jq --color-output .
  usage
fi

if [[ -n ${insecure+x} ]]; then
    options="-k"
fi

if [[ -z ${tre_url} ]]; then
  # access_token specified but no URL
  echo -e "No TRE URL provided\n"
  usage
fi

case "${bundle_type}" in
  ("workspace") tre_get_path="api/workspace-templates" ;;
  ("workspace_service") tre_get_path="api/workspace-service-templates" ;;
  ("user_resource") tre_get_path="api/workspace-service-templates/${workspace_service_name}/user-resource-templates";;
  ("shared_service") tre_get_path="api/shared-service-templates";;
esac

register_result=$(curl -i -X "POST" "${tre_url}/${tre_get_path}" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer ${access_token}" -d "${payload}" "${options}")
get_http_code "${register_result}"
if [[ ${http_code} == 409 ]]; then
  echo "Template with this version already exists"
elif [[ ${http_code} != 201 ]]; then
  echo "Error while registering template"
  echo "${register_result}"
  exit 1
fi

if [[ "${verify}" = "true" ]]; then
  # Check that the template got registered
  template_name=$(yq eval '.name' porter.yaml)
  status_code=$(curl -X "GET" "${tre_url}/${tre_get_path}/${template_name}" -H "accept: application/json" -H "Authorization: Bearer ""${access_token}""" "${options}" -s -w "%{http_code}" -o /dev/null)

  if [[ ${status_code} != 200 ]]; then
    echo "::warning ::Template API check for ${bundle_type} ${template_name} returned http status: ${status_code}"
    exit 1
  fi
fi
