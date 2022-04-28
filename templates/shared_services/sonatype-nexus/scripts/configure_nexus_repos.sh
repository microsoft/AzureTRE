#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0  [-t --tre-id]  [-l --location]

    Options:
        -t, --tre-id               ID of the TRE
        -l, --location             Location of the TRE (i.e. westeurope)
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -t | --tre-id)
        shift
        tre_id=$1
        ;;
    esac
    case $1 in
    -l | --location)
        shift
        location=$1
        ;;
    esac
    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi
    shift # remove the current value for `$1` and use the next
done

NEXUS_URL="https://nexus-${tre_id}.${location}.cloudapp.azure.com"
NEXUS_ADMIN_PASSWORD_NAME="nexus-admin-password"
KEYVAULT_NAME="kv-${tre_id}"
NEXUS_PASS=$(az keyvault secret show --name "${NEXUS_ADMIN_PASSWORD_NAME}" --vault-name "${KEYVAULT_NAME}" -o json | jq -r '.value')

if [ -z "$NEXUS_PASS" ]; then
  echo "Unable to get the Nexus admin password from Keyvault. You may need to manually reset it in the Nexus host. Refer to the public Nexus documentation for more information."
  exit 1
fi

# Create proxy for each .json file
for filename in "$(dirname "${BASH_SOURCE[0]}")"/nexus_repos_config/*.json; do
    echo "Found config file: $filename. Sending to Nexus..."
    # Check if apt proxy
    base_type=$( jq .baseType "$filename" | sed 's/"//g')
    repo_type=$( jq .repoType "$filename" | sed 's/"//g')
    repo_name=$(jq .name "$filename" | sed 's/"//g')

    base_url=$NEXUS_URL/service/rest/v1/repositories/$base_type/$repo_type
    full_url=$base_url/$repo_name

    STATUS_CODE=$(curl -iu admin:"$NEXUS_PASS" -X "GET" "$full_url" -H "accept: application/json" -k -s -w "%{http_code}" -o /dev/null)
    echo "Response received from Nexus: $STATUS_CODE"

    if [[ ${STATUS_CODE} == 404 ]]
    then
        curl -iu admin:"$NEXUS_PASS" -XPOST \
        "$base_url" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$filename"
    else
        echo "$repo_type proxy for $repo_name already exists."
    fi
done
