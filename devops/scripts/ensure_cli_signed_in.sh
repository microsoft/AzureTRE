#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# Uncomment this line to see each command for debugging (careful: this will show secrets!)
# set -o xtrace

base_url="${TRE_URL}"
cli_env_file="${HOME}/.config/tre/environment.json"
# Are we already signed in?
already_signed_in=0
got_token_from_cli=$(tre get-token >/dev/null 2>&1; echo $?)
if [[ $got_token_from_cli == "0" ]]; then
  if [ -f "${cli_env_file}" ] && [ "${base_url}" == "$(jq -r '."base-url"' "${cli_env_file}")" ]; then
    already_signed_in=1
  fi
fi

if [ $already_signed_in == 1 ]; then
  echo "CLI already signed in"
else
  if [ -n "${TEST_ACCOUNT_CLIENT_ID:-}" ] && [ -n "${TEST_ACCOUNT_CLIENT_SECRET:-}" ] && [ -n "${AAD_TENANT_ID:-}" ] && [ -n "${API_CLIENT_ID:-}" ]; then
    # Use client credentials flow with TEST_ACCOUNT_CLIENT_ID/SECRET
    echo "Using TEST_ACCOUNT_CLIENT_ID to sign in to tre CLI"
    tre login client-credentials \
      --base-url "${base_url}" \
      --client-id "$TEST_ACCOUNT_CLIENT_ID" \
      --client-secret "$TEST_ACCOUNT_CLIENT_SECRET" \
      --aad-tenant-id "$AAD_TENANT_ID" \
      --api-scope "api://${API_CLIENT_ID}" \
      --no-verify  # skip SSL verification in case certs aren't set up
  else
    # Use resource owner password credentials flow with USERNAME/PASSWORD
    echo "tre CLI not already signed in and missing one of TEST_ACCOUNT_CLIENT_ID, TEST_ACCOUNT_CLIENT_SECRET, AAD_TENANT_ID or API_CLIENT_ID"
    exit 1
  fi
fi
