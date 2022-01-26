#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0 [-u --tre_url]  [-c --current] [-i --insecure]

    Options:
        -r, --acr-name        Azure Container Registry Name
        -t, --bundle-type     Bundle type, workspace or workspace_service
        -c, --current:        Make this the currently deployed version of this template
        -i, --insecure:       Bypass SSL certificate checks
        -u, --tre_url:        URL for the TRE (required for automatic registration)
        -a, --access-token    Azure access token to automatically post to the API (required for automatic registration)
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

current="false"

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
    *)
        usage
        ;;
    esac
    shift # remove the current value for `$1` and use the next
done

if [[ -z ${bundle_type+x} ]]; then
    echo -e "No bundle type provided\n"
    usage
fi

# This script assumes that it is being run in the BUNDLE_DIR so we can take the
# current working directory
BUNDLE_DIR="$(pwd)"
TEMPLATE_NAME=$(yq eval '.name' ${BUNDLE_DIR}/porter.yaml)

case "${bundle_type}" in
  ("workspace") TRE_GET_PATH="api/workspace-templates" ;;
  ("workspace_service") TRE_GET_PATH="api/workspace-service-templates" ;;
esac

curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d \
  "grant_type=password&resource=${TF_VAR_api_client_id}&client_id=${CLIENT_ID}&username=${USERNAME}&password=${PASSWORD}&scope=default)" \
  https://login.microsoftonline.com/${TF_VAR_aad_tenant_id}/oauth2/token | jq -r '.access_token'

