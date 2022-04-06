#!/bin/bash
set -e

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
# Create a .gitignore'd  directory for temp output
mkdir -p "$DIR/script_tmp"
echo '*' > "$DIR/script_tmp/.gitignore"

api_response_file="$DIR/script_tmp/api_response.txt"

echo "Calling /health endpoint..."
response_code=$(curl --insecure --silent --output "$api_response_file" --write-out "%{http_code}" "https://${TRE_ID}.${LOCATION}.cloudapp.azure.com/api/health")

# Add retries in case the backends aren't up yet
retries_left=5
while [[ "${response_code}" != "200" ]] && [[ $retries_left -ge 0 ]]; do
  echo "Calling /health endpoint... ($retries_left retries left)"
  response_code=$(curl --insecure --silent --output "$api_response_file" --write-out "%{http_code}" "https://${TRE_ID}.${LOCATION}.cloudapp.azure.com/api/health")
  retries_left=$(( retries_left - 1))
  sleep 30
done

if [[ "$response_code" != "200" ]]; then
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Non-success code returned: $response_code"
  echo "Response:"
  cat "$api_response_file"
  exit 1
fi

not_ok_count=$(jq -r '[.services | .[] | select(.status!="OK")] | length' < "$api_response_file")

if [[ "$not_ok_count" == "0" ]]; then
  echo "*** ✅ API healthy ***"
else
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Unhealthy services:"
  jq -r '[.services | .[] | select(.status!="OK")]' < "$api_response_file"
  exit 1
fi
