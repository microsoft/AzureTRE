#!/bin/bash
set -e

if [ -z "$1" ]
  then
    echo 'Nexus password needs to be passed as argument'
fi

# Create proxy for each .json file
for filename in "$(dirname "${BASH_SOURCE[0]}")"/nexus_repos_config/*.json; do
    echo "Found config file: $filename. Sending to Nexus..."
    # Check if apt proxy
    base_type=$( jq .baseType "$filename" | sed 's/"//g')
    repo_type=$( jq .repoType "$filename" | sed 's/"//g')
    repo_name=$(jq .name "$filename" | sed 's/"//g')

    base_url=http://localhost/service/rest/v1/repositories/$base_type/$repo_type
    full_url=$base_url/$repo_name

    status_code=$(curl -iu admin:"$1" -X "GET" "$full_url" -H "accept: application/json" -k -s -w "%{http_code}" -o /dev/null)
    echo "Response received from Nexus: $status_code"

    if [[ ${status_code} == 404 ]]
    then
        curl -iu admin:"$1" -XPOST \
        "$base_url" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$filename"
    else
        echo "$repo_type proxy for $repo_name already exists."
    fi
done
