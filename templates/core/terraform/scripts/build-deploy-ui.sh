#!/bin/bash
set -e

pushd ./ui/app

# replace the values in the config file
jq --arg rootClientId "${SWAGGER_UI_CLIENT_ID}" \
  --arg rootTenantId "${AAD_TENANT_ID}" \
  --arg treApiClientId "${API_CLIENT_ID}" \
  --arg treUrl "https://${FQDN}/api" \
  '.rootClientId = $rootClientId | .rootTenantId = $rootTenantId | .treApiClientId = $treApiClientId | .treUrl = $treUrl' ./src/config.sample.json > ./src/config.json

yarn install
yarn build
SWA_CLI_DEPLOYMENT_TOKEN="${UI_API_KEY}" swa deploy -a ./build -n "${TRE_ID}"-ui --env ""
echo "TRE UI deployed. Please add the above URI as a Redirect URI in the AAD 'TRE Client Apps (swagger app)' app. This is currently a manual step."

popd

