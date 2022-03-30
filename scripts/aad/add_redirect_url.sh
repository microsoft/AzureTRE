#!/bin/bash

# This script is called by a bundle to interact with the TRE API

function usage() {
    cat <<USAGE

    Usage: $0 [--redirect-url]

    Options:
        --auth-tenant-id          The tenant that we are using to authentciate against
        --workspace-client-id     The client id of the Workspace API
        --workspace-client-secret The client secret of the Workspace API
        --workspace-object-id     The object id of the Workspace API
        --redirect-url            URL for the redirect to add to the workspace
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    --redirect-url)
        shift
        redirect_url=$1
        ;;
    --auth-tenant-id)
        shift
        auth_tenant_id=$1
        ;;
    --workspace-client-id)
        shift
        workspace_client_id=$1
        ;;
    --workspace-client-secret)
        shift
        workspace_client_secret=$1
        ;;
    --workspace-object-id)
        shift
        workspace_object_id=$1
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

if [[ -z ${redirect_url:-} ]]; then
    echo -e "No redirect url provided.\n"
    usage
fi

token_response=$(curl -X POST \
  "https://login.microsoftonline.com/${auth_tenant_id}/oauth2/v2.0/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${workspace_client_id}"   \
  -d "grant_type=client_credentials"   \
  -d "scope=https%3A%2F%2Fgraph.microsoft.com%2F.default"   \
  -d "client_secret=${workspace_client_secret}")

if [ -n "${token_response:-}" ]; then
  access_token=$(echo "${token_response}" | jq -r .access_token)
  if [[ ${access_token} == "null" ]]; then
      echo "Failed to obtain auth token for API:"
      echo "${token_response}"
      exit 2
  fi
fi

web=$(curl -X "GET" "https://graph.microsoft.com/v1.0/applications/${workspace_object_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${access_token}" \
  | jq -r --arg redirectUri "${redirect_url}" \
  ' .web.redirectUris += [$redirectUri] | .web.implicitGrantSettings.enableAccessTokenIssuance = true | .web.implicitGrantSettings.enableIdTokenIssuance = true | {web}')

echo -e "Patching ${web} \nto https://graph.microsoft.com/v1.0/applications/${workspace_object_id}"
curl -X "PATCH" "https://graph.microsoft.com/v1.0/applications/${workspace_object_id}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${access_token}" \
  -d "${web}"
