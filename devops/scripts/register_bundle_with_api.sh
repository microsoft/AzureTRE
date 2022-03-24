#!/bin/bash

# This script register a bundle with the TRE API. It relies on the bundle
# pre-existing in the remote repository (i.e. has been publish beforehand).

# set -o errexit
set -o pipefail
set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -r, --acr-name                Azure Container Registry Name
        -t, --bundle-type             Bundle type: workspace, workspace_service, user_resource or shared_service
        -w, --workspace-service-name  The template name of the user resource (if registering a user_resource), or shared service (if registering a shared_service)
        -c, --current                 Make this the currently deployed version of this template
        -i, --insecure                Bypass SSL certificate checks
        -u, --tre_url                 URL for the TRE (required for automatic registration)
        -a, --access-token            Azure access token to automatically post to the API (required for automatic registration)
        -v, --verify                  Verify registration with the API
        -d, --deploy_shared_service   If registering a shared service bundle, deploy it as well
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [[ $# -eq 0 ]]; then
    usage # run usage function
fi

current="false"
verify="false"
deploy_shared_service="false"

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
    -d | --deploy_shared_service)
        deploy_shared_service="true"
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

if [ ${bundle_type} == "user_resource" ] && [ -z ${workspace_service_name:-} ]; then
    echo -e "You must supply a workspace_service_name name if you are registering a user_resource bundle\n"
    usage
fi

if [ "${deploy_shared_service}" = "true" ] && [ ${bundle_type} != "shared_service" ]; then
    echo -e "You can only deploy a shared_service bundle via this script\n"
    usage
fi

explain_json=$(porter explain --reference ${acr_name}.azurecr.io/$(yq eval '.name' porter.yaml):v$(yq eval '.version' porter.yaml) -o json)

payload=$(echo ${explain_json} | jq --argfile json_schema template_schema.json --arg current "${current}" --arg bundle_type "${bundle_type}" '. + {"json_schema": $json_schema, "resourceType": $bundle_type, "current": $current}')

if [ -z "${access_token:-}" ]
then
  # We didn't get an access token but we can try to generate one.
  if [ ! -z "${AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID:-}" ] && [ ! -z "${AUTOMATION_ADMIN_ACCOUNT_CLIENT_SECRET:-}" ] && [ ! -z "${AAD_TENANT_ID:-}" ] && [ ! -z "${API_CLIENT_ID:-}" ]
  then
    # Use client credentials flow with AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID/SECRET
    echo "Using AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID to get token via client credential flow"
    token_response=$(curl -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
      https://login.microsoftonline.com/${AAD_TENANT_ID}/oauth2/v2.0/token \
      -d "client_id=${AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID}"   \
      -d 'grant_type=client_credentials'   \
      -d "scope=api://${API_CLIENT_ID}/.default"   \
      -d "client_secret=${AUTOMATION_ADMIN_ACCOUNT_CLIENT_SECRET}")
  elif [ ! -z "${API_CLIENT_ID:-}" ] && [ ! -z "${TEST_APP_ID:-}" ] && [ ! -z "${TEST_USER_NAME:-}" ] && [ ! -z "${TEST_USER_PASSWORD:-}" ] && [ ! -z "${AAD_TENANT_ID:-}" ]
  then
    # Use resource owner password credentials flow with USERNAME/PASSWORD
    echo "Using TEST_USER_NAME to get token via resource owner password credential flow"
    token_response=$(curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d \
      "grant_type=password&resource=${API_CLIENT_ID}&client_id=${TEST_APP_ID}&username=${TEST_USER_NAME}&password=${TEST_USER_PASSWORD}&scope=default)" \
      https://login.microsoftonline.com/${AAD_TENANT_ID}/oauth2/token)
  fi

  if [ ! -z "${token_response:-}" ]
  then
    access_token=$(echo ${token_response} | jq -r .access_token)
    if [[ ${access_token} == "null" ]]; then
        echo "Failed to obtain auth token for API:"
        echo ${token_response}
        exit 2
    fi
  fi
fi

if [ -z "${access_token:-}" ]
then
  echo "API access token isn't available - automatic bundle registration not possible. Use the script output to self-register. See documentation for more details."
  echo $(echo ${payload} | jq --color-output .)
else
  if [[ -n ${insecure+x} ]]; then
      options=" -k"
  fi

  if [[ -z ${tre_url} ]]; then
    # access_token specified but no URL
    echo -e "No TRE URL provided\n"
    usage
  fi

  case "${bundle_type}" in
    ("workspace") tre_get_path="api/workspace-templates" ;;
    ("workspace_service") tre_get_path="api/workspace-service-templates" ;;
    ("user_resource") tre_get_path="/api/workspace-service-templates/${workspace_service_name}/user-resource-templates";;
    ("shared_service") tre_get_path="/api/shared-service-templates";;
  esac

  # echo -e "Server Response:\n"
  # eval "curl -X 'POST' ${tre_url}/${tre_get_path} -H 'accept: application/json' -H 'Content-Type: application/json' -H 'Authorization: Bearer ${access_token}' -d '${payload}' ${options}"
  # echo -e "\n"

  if [[ "${verify}" = "true" ]]; then
    # Check that the template got registered
    template_name=$(yq eval '.name' porter.yaml)
    status_code=$(curl -X "GET" "${tre_url}/${tre_get_path}/${template_name}" -H "accept: application/json" -H "Authorization: Bearer ${access_token}" ${options} -s -w "%{http_code}" -o /dev/null)

    if [[ ${status_code} != 200 ]]; then
      echo "::warning ::Template API check for ${bundle_type} ${template_name} returned http status: ${status_code}"
      exit 1
    fi
  fi

  if [[ "${deploy_shared_service}" = "true" ]]; then
    echo DEPLOYING

    template_name=$(yq eval '.name' porter.yaml)
    payload="{ \"templateName\": \"${template_name}\", \"properties\": { \"display_name\": \"Shared service ${template_name}\", \"description\": \"Automatically deployed ${template_name}\" } }"

    status_code=$(curl -X "POST" "${tre_url}/api/shared-services" -H "accept: application/json" -H "Content-Type: application/json" -H "Authorization: Bearer ${access_token}" -d "${payload}" ${options} -s -w "%{http_code}" -o /dev/null)

    if [[ ${status_code} != 202 ]]; then
      echo "::warning ::Deployment of shared service ${template_name} via API check returned http status: ${status_code}"
      exit 1
    fi
  fi
fi
