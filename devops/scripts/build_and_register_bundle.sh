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
        BUNDLE_TYPE=$1
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

if [[ -z ${BUNDLE_TYPE+x} ]]; then
    echo -e "No bundle type provided\n"
    usage
fi

# This script assumes that it is being run in the BUNDLE_DIR so we can take the
# current working directory
BUNDLE_DIR="$(pwd)"
TEMPLATE_NAME=$(yq eval '.name' ${BUNDLE_DIR}/porter.yaml)

case "${BUNDLE_TYPE}" in
  ("workspace") TRE_GET_PATH="api/workspace-templates" ;;
  ("workspace_service") TRE_GET_PATH="api/workspace-service-templates" ;;
esac

export TOKEN=$(curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d \
  "grant_type=password&resource=${RESOURCE}&client_id=${CLIENT_ID}&username=${USERNAME}&password=${PASSWORD}&scope=default)" \
  https://login.microsoftonline.com/${AUTH_TENANT_ID}/oauth2/token | jq -r '.access_token')

# We now need to traverse back to our scripts directory
# TODO: Fix this traversing
cd ../../../
make register-bundle DIR=${BUNDLE_DIR}

# Check that the template got registered
STATUS_CODE=$(curl -X "GET" "${TRE_URL}/${TRE_GET_PATH}/${TEMPLATE_NAME}" -H "accept: application/json" -H "Authorization: Bearer ${TOKEN}" -k -s -w "%{http_code}" -o /dev/null)

if [[ ${STATUS_CODE} != 200 ]]
then
  echo "::warning ::Template API check for ${BUNDLE_TYPE} ${TEMPLATE_NAME} returned http status: ${STATUS_CODE}"
  exit 1
fi
