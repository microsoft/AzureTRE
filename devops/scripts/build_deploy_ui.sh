#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# Get the directory that this script is in
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

pushd "$DIR/../../ui/app"

ui_version=$(jq -r '.version' package.json)

activeDirectoryUri="$(az cloud show --query endpoints.activeDirectory --output tsv)"

# replace the values in the config file
jq --arg rootClientId "${SWAGGER_UI_CLIENT_ID}" \
  --arg rootTenantId "${AAD_TENANT_ID}" \
  --arg treApplicationId "api://${API_CLIENT_ID}" \
  --arg treUrl "/api" \
  --arg treId "${TRE_ID}" \
  --arg version "${ui_version}" \
  --arg activeDirectoryUri "${activeDirectoryUri}" \
  --arg userManagementEnabled "${USER_MANAGEMENT_ENABLED:-False}" \
  --arg uiSiteName "${UI_SITE_NAME:-}" \
  --arg uiFooterText "${UI_FOOTER_TEXT:-}" \
  '.rootClientId = $rootClientId | .rootTenantId = $rootTenantId | .treApplicationId = $treApplicationId | .treUrl = $treUrl | .treId = $treId | .version = $version | .activeDirectoryUri = $activeDirectoryUri | .userManagementEnabled = $userManagementEnabled | .uiSiteName = $uiSiteName | .uiFooterText = $uiFooterText' ./src/config.source.json > ./src/config.json

# build and deploy the app
yarn install
yarn build

popd

CONTENT_DIR="$DIR/../../ui/app/dist" "$DIR/upload_static_web.sh"
