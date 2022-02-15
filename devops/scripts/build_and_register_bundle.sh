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

if [[ -z ${BUNDLE_TYPE+x} ]]; then
    echo -e "No bundle type provided\n"
    usage
fi


if [[ -z $AUTH_TENANT_ID ]]; then
    echo "The AUTH_TENANT_ID environment variable is not set"
    exit 1
fi

# This script assumes that it is being run in the BUNDLE_DIR so we can take the
# current working directory
BUNDLE_DIR="$(pwd)"
TEMPLATE_NAME=$(yq eval '.name' ${BUNDLE_DIR}/porter.yaml)

case "${BUNDLE_TYPE}" in
  ("workspace") TRE_GET_PATH="api/workspace-templates" ;;
  ("workspace_service") TRE_GET_PATH="api/workspace-service-templates" ;;
esac


if [[ -n $AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID && -n $AUTOMATION_ADMIN_ACCOUNT_CLIENT_SECRET ]]; then
  # Use client credentials flow with AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID/SECRET
  echo "Using AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID to get token via client credential flow"
  token_response=$(curl -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
    https://login.microsoftonline.com/$AUTH_TENANT_ID/oauth2/v2.0/token \
    -d "client_id=$AUTOMATION_ADMIN_ACCOUNT_CLIENT_ID"   \
    -d 'grant_type=client_credentials'   \
    -d "scope=api://$API_CLIENT_ID/.default"   \
    -d "client_secret=$AUTOMATION_ADMIN_ACCOUNT_CLIENT_SECRET")
else
  # Use resource owner password credentials flow with USERNAME/PASSWORD
  echo "Using USERNAME to get token via resource owner password credential flow"
  token_response=$(curl -X POST -H "Content-Type: application/x-www-form-urlencoded" -d \
    "grant_type=password&resource=${RESOURCE}&client_id=${CLIENT_ID}&username=${USERNAME}&password=${PASSWORD}&scope=default)" \
    https://login.microsoftonline.com/${AUTH_TENANT_ID}/oauth2/token)
fi

TOKEN=$(echo $token_response | jq -r .access_token)
if [[ $TOKEN == "null" ]]; then
    echo "Failed to obtain auth token for API:"
    echo $token_response
    exit 2
fi

# We now need to traverse back to our scripts directory
# TODO: Fix this traversing
cd ../../../
TOKEN=$TOKEN make register-bundle DIR=${BUNDLE_DIR}

# Check that the template got registered
STATUS_CODE=$(curl -X "GET" "${TRE_URL}/${TRE_GET_PATH}/${TEMPLATE_NAME}" -H "accept: application/json" -H "Authorization: Bearer ${TOKEN}" -k -s -w "%{http_code}" -o /dev/null)

if [[ ${STATUS_CODE} != 200 ]]
then
  echo "::warning ::Template API check for ${BUNDLE_TYPE} ${TEMPLATE_NAME} returned http status: ${STATUS_CODE}"
  exit 1
fi
