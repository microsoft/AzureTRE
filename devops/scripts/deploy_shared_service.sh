#!/bin/bash

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
#set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -u, --tre_url                 URL for the TRE (required for automatic registration)
        -a, --access-token            Azure access token to automatically post to the API (required for automatic registration)
        -i, --insecure                Bypass SSL certificate checks

        Additional bundle properties to be passed to the bundle on install can be passed in the format --propertyName propertyValue
USAGE
    exit 1
}

while [ "$1" != "" ]; do
    case $1 in
    -u | --tre_url)
        shift
        tre_url=$1
        ;;
    -i| --insecure)
        insecure=1
        ;;
    -a | --access-token)
        shift
        access_token=$1
        ;;
    --*)
        property_names+=("${1:2}")
        shift
        property_values+=("$1")
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

if [[ -n ${insecure+x} ]]; then
    options="-k"
fi

if [[ -z ${tre_url} ]]; then
  echo -e "No TRE URL provided\n"
  usage
fi

if [ -z "${access_token:-}" ]; then
  # If access token isn't set, try to use environment variables
  if [ -z "${ACCESS_TOKEN:-}" ]
  then
    echo "Please provide an API access token to deploy shared service"
    exit 1
  fi
  access_token=${ACCESS_TOKEN}
fi

template_name=$(yq eval '.name' porter.yaml)
template_version=$(yq eval '.version' porter.yaml)
echo "Deploying shared service ${template_name} of version ${template_version}"

function get_http_code() {
  curl_output="$1"
  http_code=$(echo "${curl_output}" | grep HTTP | sed 's/.*HTTP\/1\.1 \([0-9]\+\).*/\1/' | tail -n 1)
}

function wait_for_operation_result() {
  operation_id="$1"
  shared_service_id="$2"
  expected_status="$3"

  while : ; do
    # Poll for the result of operation
    get_operation_result=$(curl -i -X "GET" "${tre_url}"/api/shared-services/"${shared_service_id}"/operations/"${operation_id}" \
                           -H "accept: application/json" \
                           -H "Content-Type: application/json" \
                           -H "Authorization: Bearer ""${access_token}""" "${options}" -s)
    get_http_code "${get_operation_result}"
    if [[ "${http_code}" != 200 ]] && [[ "${http_code}" != 202 ]]; then
      if [[ "${http_code}" != 408 ]] && [[ "${http_code}" != 502 ]] && [[ "${http_code}" != 503 ]] && [[ "${http_code}" != 504 ]]; then
        echo "Got a non-retrieable HTTP status code: ${http_code}"
        echo "${get_operation_result}"
        exit 1
      fi
      echo "Got HTTP code ${http_code}, retrying..."
    else
      operation_status=$(echo "${get_operation_result}" | grep '{' | jq -r .operation.status)
      echo "Waiting for deployment of ""${template_name}"" to finish... (current status: ""${operation_status}"")"
      sleep 5
    fi

    if [[ "${operation_status}" == "${expected_status}" ]] || [[ "${operation_status}" == *"failed"* ]]; then
      break
    fi
  done

  if [[ "${operation_status}" != "${expected_status}" ]]; then
    echo "Failed to await operation ${operation_id} (status is ""${operation_status}""). Please check resource processor logs"
    exit 1
  fi
}

curl_settings=(--retry 7 --retry-max-time 300 --max-time 90)

# Get shared services and determine if the given shared service has already been deployed
get_shared_services_result=$(curl -i "${curl_settings[@]}" -X "GET" "${tre_url}"/api/shared-services \
                             -H "accept: application/json" \
                             -H "Content-Type: application/json" \
                             -H "Authorization: Bearer ""${access_token}""" "${options}" -s)
get_http_code "${get_shared_services_result}"
if [[ "${http_code}" != 200 ]]; then
  echo "Failed to get shared services ${template_name}"
  echo "${get_shared_services_result}"
  exit 1
fi

deployed_shared_service=$(echo "${get_shared_services_result}" \
  | grep '{' \
  | jq -r ".sharedServices[] | select(.templateName == \"${template_name}\" and .deploymentStatus == \"deployed\")")

if [[ -n "${deployed_shared_service}" ]]; then
  # Get template version of the service already deployed
  deployed_version=$(echo "${deployed_shared_service}" | jq -r ".templateVersion")

  if [[ "${template_version}" == "${deployed_version}" ]]; then
    echo "Shared service ${template_name} of version ${template_version} has already been deployed"
    exit 0
  else
    echo "Resource upgrade isn't currently implemented. See https://github.com/microsoft/AzureTRE/issues/141"
    exit 0
  fi
fi

# Add additional properties to the payload JSON string
additional_props=""
for index in "${!property_names[@]}"; do
  name=${property_names[$index]}
  value=${property_values[$index]}
  additional_props="$additional_props, \"$name\": \"$value\""
done

payload="{ \"templateName\": \"""${template_name}""\", \"properties\": { \"display_name\": \"Shared service ""${template_name}""\", \"description\": \"Automatically deployed ""${template_name}""\"${additional_props} } }"
deploy_result=$(curl -i "${curl_settings[@]}" -X "POST" "${tre_url}/api/shared-services" \
                -H "accept: application/json" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer ""${access_token}""" -d "${payload}" "${options}" -s)
get_http_code "${deploy_result}"
if [[ "${http_code}" == 409 ]]; then
  echo "Shared service ${template_name} has already been deployed"
  exit 0
fi
if [[ "${http_code}" != 202 ]]; then
  echo "Failed to deploy shared service: ${http_code}"
  echo "${deploy_result}"
  exit 1
fi
json_deploy_result=$(echo "${deploy_result}" | grep '{')
operation_id=$(echo "${json_deploy_result}" | jq -r .operation.id)
operation_status=$(echo "${json_deploy_result}" | jq -r .operation.status)
shared_service_id=$(echo "${json_deploy_result}" | jq -r .operation.resourceId)

wait_for_operation_result "${operation_id}" "${shared_service_id}" "deployed"

echo "Deployed shared service ""${template_name}"""
