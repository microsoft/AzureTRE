#!/bin/bash
set -e

echo "Calling /health endpoint..."
response_code=$(curl --insecure --silent --output api-response.txt --write-out "%{http_code}" "https://${TRE_ID}.${LOCATION}.cloudapp.azure.com/api/health")

echo "Got response from https://${TRE_ID}.${LOCATION}.cloudapp.azure.com/api/health:"
cat "api-response.txt"
echo

if [[ "$response_code" != "200" ]]; then
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Non-success code returned: $response_code"
  exit 1
fi

not_ok_count=$(jq -r '[.services | .[] | select(.status!="OK")] | length' < api-response.txt)

if [[ "$not_ok_count" == "0" ]]; then
  echo "*** ✅ API healthy ***"
else
  echo "*** ⚠️ API _not_ healthy ***"
  echo "Unhealthy services:"
  jq -r '[.services | .[] | select(.status!="OK")]' < api-response.txt
  exit 1
fi
