#!/bin/bash

# This script register a bundle with the TRE API. It relies on the bundle
# pre-existing in the remote repository (i.e. has been publish beforehand).

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

function usage() {
    cat <<USAGE

    Usage: $0 [-c --current] [-i --insecure]

    Options:
        -r, --acr-name                Azure Container Registry Name
        -t, --bundle-type             Bundle type: workspace, workspace_service, user_resource or shared_service
        -w, --workspace-service-name  The template name of the user resource (if registering a user_resource)
        -c, --current                 Make this the currently deployed version of this template
        -v, --verify                  Verify registration with the API
        --dry-run                     Don't submit the template to the API, just output the payload
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

current="false"
verify="false"
dry_run="false"

while [ "$1" != "" ]; do
    case $1 in
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
    -v| --verify)
        verify="true"
        ;;
    --dry-run)
        dry_run="true"
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

acr_domain_suffix=$(az cloud show --query suffixes.acrLoginServerEndpoint --output tsv)
explain_json=$(porter explain --reference "${acr_name}${acr_domain_suffix}"/"$(yq eval '.name' porter.yaml)":v"$(yq eval '.version' porter.yaml)" -o json)

payload=$(echo "${explain_json}" | jq --slurpfile json_schema template_schema.json --arg current "${current}" --arg bundle_type "${bundle_type}" '. + {"json_schema": $json_schema[0], "resourceType": $bundle_type, "current": $current}')

if [ "${dry_run}" == "true" ]; then
    echo "--dry-run specified - automatic bundle registration disabled. Use the script output to self-register. "
    echo "See documentation for more details: https://microsoft.github.io/AzureTRE/tre-admins/registering-templates/"
    echo "${payload}" | jq --color-output .
    exit 1
fi

if [ "${bundle_type}" == "user_resource" ] && [ -z "${workspace_service_name:-}" ]; then
  echo -e "You must supply a workspace service_name name if you would like to automatically register the user_resource bundle\n"
  echo "${payload}" | jq --color-output .
  usage
fi

template_name=$(yq eval '.name' porter.yaml)
template_version=$(yq eval '.version' porter.yaml)


function get_template() {
  case "${bundle_type}" in
    ("workspace") get_result=$(tre workspace-template "$template_name" show --output json) || echo ;;
    ("workspace_service") get_result=$(tre workspace-service-template "$template_name" show --output json) || echo ;;
    ("user_resource") get_result=$(tre workspace-service-template "${workspace_service_name}" user-resource-template "$template_name" show --output json) || echo;;
    ("shared_service") get_result=$(tre shared-service-template "$template_name" show --output json) || echo ;;
  esac
  echo "$get_result"
}


get_result=$(get_template)
if [[ -n "$(echo "$get_result" | jq -r .id)" ]]; then
  # 'id' was returned - so we successfully got the template from the API. Now check the version
  if [[ "$(echo "$get_result" | jq -r .version)" == "$template_version" ]]; then
    echo "Template with this version already exists"
    exit
  fi
else
  error_code=$(echo "$get_result" | jq -r .status_code)
  # 404 Not Found error at this point is fine => we want to continue to register the template
  # For other errors, show the error and exit with non-zero result
  if [[  "$error_code" != "404" ]]; then
    echo "Error checking for existing template: $get_result"
    exit 1
  fi
fi


# If we got here then register the template - CLI exits with non-zero result on error
case "${bundle_type}" in
  ("workspace") tre workspace-templates new --definition "${payload}" ;;
  ("workspace_service") tre workspace-service-templates new --definition "${payload}" ;;
  ("user_resource") tre workspace-service-template "${workspace_service_name}" user-resource-templates new --definition "${payload}" ;;
  ("shared_service") tre shared-service-templates new --definition "${payload}";;
esac

if [[ "${verify}" = "true" ]]; then
  # Check that the template got registered

  get_result=$(get_template)
  if [[ -z "$(echo "$get_result" | jq -r .id)" ]]; then
    echo "Error checking for template after registering: $get_result"
    exit 1
  fi
fi
