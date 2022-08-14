#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pushd "$DIR/../../ui/app"

# replace the values in the config file
jq --arg rootClientId "${SWAGGER_UI_CLIENT_ID}" \
  --arg rootTenantId "${AAD_TENANT_ID}" \
  --arg treApplicationId "api://${API_CLIENT_ID}" \
  --arg treUrl "https://${FQDN}/api" \
  '.rootClientId = $rootClientId | .rootTenantId = $rootTenantId | .treApplicationId = $treApplicationId | .treUrl = $treUrl' ./src/config.source.json > ./src/config.json

# build and deploy the app
yarn install
yarn build

popd

CONTENT_DIR="$DIR/../../ui/app/build" "$DIR/upload_static_web.sh"
