#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

pushd ./ui/app

# replace the values in the config file
jq --arg rootClientId "${SWAGGER_UI_CLIENT_ID}" \
  --arg rootTenantId "${AAD_TENANT_ID}" \
  --arg treApiClientId "${API_CLIENT_ID}" \
  --arg treUrl "https://${FQDN}/api" \
  '.rootClientId = $rootClientId | .rootTenantId = $rootTenantId | .treApiClientId = $treApiClientId | .treUrl = $treUrl' ./src/config.source.json > ./src/config.json

# build and deploy the app
yarn install
yarn build

popd

DIR=./ui/app/build ./devops/scripts/upload_static_web.sh
