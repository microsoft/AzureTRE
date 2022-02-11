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
access_token=

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

if [[ -z ${access_token} ]]; then
    echo -e "WARNING!!! No Azure access token provided. Automatic bundle registration not possible. Use the script output to self-register. See documentation for more details.\n"
else
  if [[ -z ${tre_url} ]]; then
    # access_token specified but no URL
    echo -e "No TRE URL provided\n"
    usage
  fi
fi

if [[ -z ${acr_name} ]]; then
    echo -e "No Azure Container Registry name provided\n"
    usage
fi

if [[ -z ${bundle_type} ]]; then
    echo -e "No bundle type provided\n"
    usage
fi

az acr login --name $acr_name

porter publish --registry "$acr_name.azurecr.io" --debug

explain_json=$(porter explain -o json)

payload=$(echo $explain_json | jq --argfile json_schema template_schema.json --arg current "$current" --arg bundle_type "$bundle_type" '. + {"json_schema": $json_schema, "resourceType": $bundle_type, "current": $current}')

if [[ -n  ${access_token} ]]; then
    if [[ -n ${insecure+x} ]]; then
        options=" -k"
    fi

    echo -e "Server Response:\n"

    if [[ $bundle_type == workspace ]]
    then
      curl -X 'POST'  $tre_url/api/workspace-templates -H 'accept: application/json'  -H 'Content-Type: application/json'  -H "Authorization: Bearer $access_token" -d "$payload"  $options
    else
      curl -X 'POST'  $tre_url/api/workspace-service-templates -H 'accept: application/json'  -H 'Content-Type: application/json'  -H "Authorization: Bearer $access_token" -d "$payload"  $options
    fi
    echo -e "\n"
else
    echo -e "Use the following payload to register the template:\n\n"
    echo $(echo $payload | jq --color-output .)
fi
