#!/bin/bash

set -o errexit
set -o pipefail
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

activeDirectoryUri="$(az cloud show --query endpoints.activeDirectory --output tsv)"

# Use client credentials flow with TEST_ACCOUNT_CLIENT_ID/SECRET
echo "Using TEST_ACCOUNT_CLIENT_ID to get token via client credential flow"
token_response=$(curl -X POST -H 'Content-Type: application/x-www-form-urlencoded' \
  "${activeDirectoryUri}/${AAD_TENANT_ID}"/oauth2/v2.0/token \
  -d "client_id=${TEST_ACCOUNT_CLIENT_ID}"   \
  -d 'grant_type=client_credentials'   \
  -d "scope=api://${API_CLIENT_ID}/.default"   \
  -d "client_secret=${TEST_ACCOUNT_CLIENT_SECRET}")

if [ -n "${token_response:-}" ]
then
  ACCESS_TOKEN=$(echo "${token_response}" | jq -r .access_token)
  if [[ "${ACCESS_TOKEN}" == "null" ]]; then
      echo "Failed to obtain auth token for API:"
      echo "${token_response}"
      exit 2
  fi
  export ACCESS_TOKEN
fi
