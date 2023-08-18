#!/bin/bash
set -o pipefail
set -o nounset
# set -o xtrace

if [ -z "$1" ]
  then
    echo 'Nexus password needs to be passed as argument'
fi

timeout=300
echo 'Checking for ./nexus_repos_config directory...'
while [ ! -d "$(dirname "${BASH_SOURCE[0]}")"/nexus_repos_config ]; do
  # Wait for /tmp/nexus_repos_config with json config files to be copied into vm
  if [ $timeout == 0 ]; then
    echo 'ERROR - Timeout while waiting for nexus_repos_config directory'
    exit 1
  fi
  sleep 1
  ((timeout--))
done

# Create proxy for each .json file
for filename in "$(dirname "${BASH_SOURCE[0]}")"/nexus_repos_config/*.json; do
    echo "Found config file: $filename. Sending to Nexus..."
    # Check if apt proxy
    base_type=$( jq .baseType "$filename" | sed 's/"//g')
    repo_type=$( jq .repoType "$filename" | sed 's/"//g')
    repo_name=$(jq .name "$filename" | sed 's/"//g')
    base_url=http://localhost/service/rest/v1/repositories/$base_type/$repo_type

    config_timeout=300
    status_code=1
    while [ $status_code != 201 ]; do
      status_code=$(curl -iu admin:"$1" -XPOST \
        "$base_url" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$filename" \
        -k -s -w "%{http_code}" -o /dev/null)
      echo "Response received from Nexus: $status_code"

      if [ $config_timeout == 0 ]; then
        echo "ERROR - Timeout while trying to configure $repo_name"
        exit 1
      elif [ "$status_code" != 201 ]; then
        sleep 1
        ((config_timeout--))
      fi
    done
done

# Configure realms required for repo authentication
echo 'Configuring realms...'
status_code=$(curl -iu admin:"$1" -XPUT \
  'http://localhost/service/rest/v1/security/realms/active' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @"$(dirname "${BASH_SOURCE[0]}")"/nexus_realms_config.json \
  -k -s -w "%{http_code}" -o /dev/null)
echo "Response received from Nexus: $status_code"
