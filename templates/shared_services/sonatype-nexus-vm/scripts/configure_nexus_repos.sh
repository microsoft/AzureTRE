#!/bin/bash
set -o pipefail
set -o nounset
# set -o xtrace

if [ -z "$1" ]; then
  echo 'Nexus password needs to be passed as argument'
  exit 1
fi

retry_with_backoff() {
  local func="$1"
  shift
  local sleep_time=10
  local max_sleep=180

  while [ "$sleep_time" -lt "$max_sleep" ]; do
    if "$func" "$@"; then
      return 0
    fi
    sleep "$sleep_time"
    sleep_time=$((sleep_time * 2))
  done
  return 1
}

check_repos_config() {
  [ -d "$(dirname "${BASH_SOURCE[0]}")/nexus_repos_config" ]
}

echo 'Checking for ./nexus_repos_config directory...'
if ! retry_with_backoff check_repos_config; then
  echo 'ERROR - Timeout while waiting for nexus_repos_config directory'
  exit 1
fi

nexus_ready() {
  curl -s http://localhost/service/rest/v1/status -k > /dev/null
}

echo 'Waiting for Nexus service to be fully available...'
if ! retry_with_backoff nexus_ready; then
  echo 'ERROR - Timeout while waiting for Nexus to be available'
  exit 1
fi

echo "Getting current anonymous settings in Nexus..."
current_anon_json=$(curl -iu admin:"$1" -X GET \
  'http://localhost/service/rest/v1/security/anonymous' \
  -H 'accept: application/json' \
  -k -s)
echo "Current anonymous settings: $current_anon_json"

echo "Enabling anonymous access in Nexus..."
anon_status_code=$(curl -iu admin:"$1" -X PUT \
  'http://localhost/service/rest/v1/security/anonymous' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"enabled": true}' \
  -k -s -w "%{http_code}" -o /dev/null)
echo "Response received from Nexus for enabling anonymous access: $anon_status_code"
if [ "$anon_status_code" -ne 200 ]; then
    echo "ERROR - Failed to enable anonymous access."
    exit 1
fi

echo "Configuring Nexus repositories..."
# Create proxy for each .json file
for filename in "$(dirname "${BASH_SOURCE[0]}")"/nexus_repos_config/*.json; do
    echo "Found config file: $filename. Sending to Nexus..."
    base_type=$( jq .baseType "$filename" | sed 's/"//g')
    repo_type=$( jq .repoType "$filename" | sed 's/"//g')
    repo_name=$( jq .name "$filename" | sed 's/"//g')
    base_url="http://localhost/service/rest/v1/repositories/$base_type/$repo_type"

    configure_repo() {
      local file="$1"
      local url="$2"
      local pass="$3"
      local code
      code=$(curl -iu admin:"$pass" -XPOST \
        "$url" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$file" \
        -k -s -w "%{http_code}" -o /dev/null)
      echo "Response received from Nexus: $code"
      [ "$code" -eq 201 ]
    }

    if ! retry_with_backoff configure_repo "$filename" "$base_url" "$1"; then
      echo "ERROR - Timeout while trying to configure $repo_name"
      exit 1
    fi
done

echo 'Configuring realms...'
status_code=$(curl -iu admin:"$1" -XPUT \
  'http://localhost/service/rest/v1/security/realms/active' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @"$(dirname "${BASH_SOURCE[0]}")"/nexus_realms_config.json \
  -k -s -w "%{http_code}" -o /dev/null)
echo "Response received from Nexus: $status_code"
