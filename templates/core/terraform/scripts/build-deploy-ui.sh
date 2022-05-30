#!/bin/bash
set -e

pushd ./ui/app
yarn install
yarn build
SWA_CLI_DEPLOYMENT_TOKEN="${UI_API_KEY}" swa deploy -a ./build -n "${TRE_ID}"-ui --env ""
popd

