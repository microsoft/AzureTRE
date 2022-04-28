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

nexus_url="https://nexus-${tre_id}.${location}.cloudapp.azure.com"
nexus_admin_password_name="nexus-admin-password"
keyvault_name="kv-${tre_id}"
nexus_pass=$(az keyvault secret show --name "${nexus_admin_password_name}" --vault-name "${keyvault_name}" -o json | jq -r '.value')

if [ -z "$nexus_pass" ]; then
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

    base_url=$nexus_url/service/rest/v1/repositories/$base_type/$repo_type
    full_url=$base_url/$repo_name

    status_code=$(curl -iu admin:"$nexus_pass" -X "GET" "$full_url" -H "accept: application/json" -k -s -w "%{http_code}" -o /dev/null)
    echo "Response received from Nexus: $status_code"

    if [[ ${status_code} == 404 ]]
    then
        curl -iu admin:"$nexus_pass" -XPOST \
        "$base_url" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$filename"
    else
        echo "$repo_type proxy for $repo_name already exists."
    fi
done
