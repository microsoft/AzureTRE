#!/bin/bash

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

function usage() {
    cat <<USAGE
    Usage: $0 --workspace-api-client-id some_guid --aad-redirect-uris-b64 json_array_of_urls_in_base64 --register-aad-application false
    Options:
        --workspace-api-client-id     The workspace api AAD application registration client Id
        --aad-redirect-uris-b64       The allowed redirect urls for the application
        --register-aad-application    This script runs only if this value is set to false
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    --workspace-api-client-id)
        shift
        workspace_api_client_id=$1
        ;;
    --aad-redirect-uris-b64)
        shift
        aad_redirect_uris_b64=$1
        ;;
    --register-aad-application)
        shift
        register_aad_application=$1
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

az cloud set --name "$AZURE_ENVIRONMENT"

if [ "${register_aad_application}" != "false" ]; then
    echo "This script can only run when auto-aad is disabled but got value of: ${register_aad_application}. Exiting..."
    exit 0
fi

az ad app show --id "${workspace_api_client_id}" --query web.redirectUris --only-show-errors | jq -r '. | join(" ")'

echo "urls:"
echo "${aad_redirect_uris_b64}"
echo "end of urls."

# web-redirect-uris param doesn't like any type of quotes, hence jq -r
# decode the string and read as json, then take just the values inside the object, concat lines into a space-separated
# single line, trim end.
updated_uris=$(echo "${aad_redirect_uris_b64}" | base64 --decode | jq -r '.[].value' | tr '\n' ' ' | sed 's/ *$//g')

if [ -z "${updated_uris}" ]; then
  # the azure cli command doesn't accept empty strings, so using a dummy value which will be overwriten next time
  updated_uris="http://localhost:8080/dummy"
fi

echo "Going to update application: ${workspace_api_client_id} with URIs: '${updated_uris}'"

# web-redirect-uris param doesn't like any type of quotes
# shellcheck disable=SC2086
az ad app update --id "${workspace_api_client_id}" --web-redirect-uris ${updated_uris} --only-show-errors
