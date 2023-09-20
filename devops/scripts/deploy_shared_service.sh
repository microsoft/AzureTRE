#!/bin/bash

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
#set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [--propertyName propertyValue...]

        Additional bundle properties to be passed to the bundle on install can be passed in the format --propertyName propertyValue
USAGE
    exit 1
}

while [ "$1" != "" ]; do
    case $1 in
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

template_name=$(yq eval '.name' porter.yaml)
template_version=$(yq eval '.version' porter.yaml)
echo "Deploying shared service ${template_name} of version ${template_version}"

# Get shared services and determine if the given shared service has already been deployed
get_shared_services_result=$(tre shared-services list --output json)
last_result=$?
if [[ "$last_result" != 0 ]]; then
  echo "Failed to get shared services ${template_name}"
  echo "${get_shared_services_result}"
  exit 1
fi

deployed_shared_service=$(echo "${get_shared_services_result}" \
  | jq -r ".sharedServices[] | select(.templateName == \"${template_name}\" and (.deploymentStatus != \"deleted\" or .deploymentStatus != \"deployment_failed\"))")

is_update=0
if [[ -n "${deployed_shared_service}" ]]; then
  # Get template version of the service already deployed
  deployed_version=$(echo "${deployed_shared_service}" | jq -r ".templateVersion")

  # need to check if the shared service deployment has failed, if so then we can try an update
  deployment_status=$(echo "${deployed_shared_service}" | jq -r ".deploymentStatus")
  if [[ "${deployment_status}" == "deployment_failed" ]]; then
    echo "Shared service ${template_name} of version ${template_version} has failed to deploy. Trying to update..."
    is_update=1
  elif [[ "${template_version}" == "${deployed_version}" ]]; then
    echo "Shared service ${template_name} of version ${template_version} has already been deployed"
    exit 0
  else
    is_update=1
  fi
fi

if [[ "${is_update}" -eq 0 ]]; then

  # Add additional properties to the payload JSON string
  additional_props=""
  for index in "${!property_names[@]}"; do
    name=${property_names[$index]}
    value=${property_values[$index]}
    additional_props="$additional_props, \"$name\": \"$value\""
  done

  echo "Not currently deployed - deploying..."
  display_name="${template_name#tre-shared-service-}"
  if ! deploy_result=$(cat << EOF | tre shared-services new --definition-file -
{
    "templateName": "${template_name}",
    "properties": {
        "display_name": "${display_name}",
        "description": "Automatically deployed '${template_name}'"
        ${additional_props}
    }
}
EOF
  ); then
    echo "Failed to deploy shared service:"
    echo "${deploy_result}"
    exit 1
  fi

else

  echo "An older or failed version is already deloyed. Trying to update..."
  deployed_id=$(echo "${deployed_shared_service}" | jq -r ".id")
  deployed_etag=$(echo "${deployed_shared_service}" | jq -r "._etag")
  tre shared-service "${deployed_id}" update --etag "${deployed_etag}" --definition "{\"templateVersion\": \"${template_version}\"}"

fi

echo "Deployed shared service ""${template_name}"""
