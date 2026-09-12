#!/usr/bin/env bash
set -euo pipefail

: "${RP_CLIENT_ID:?}" "${HOST_POOL_ID:?}" "${STORAGE_ACCOUNT:?}" "${LOCK_CONTAINER:?}" "${KEY_VAULT_NAME:?}" "${SECRET_NAME:?}"
az login --identity --username "$RP_CLIENT_ID" --output none
storage_args=(--account-name "$STORAGE_ACCOUNT" --container-name "$LOCK_CONTAINER" --auth-mode login --only-show-errors)
lock_ready=false
for attempt in {1..60}; do
    if exists=$(az storage blob exists "${storage_args[@]}" --name registration.lock --query exists --output tsv); then
        if [[ "$exists" == true ]] || az storage blob upload "${storage_args[@]}" --name registration.lock --file /dev/null --overwrite false --output none; then
            lock_ready=true
            break
        fi
    fi
    if [[ "$attempt" -lt 60 ]]; then sleep 5; fi
done
[[ "$lock_ready" == true ]] || { echo 'Timed out initializing the AVD registration lock; check storage access and RBAC propagation' >&2; exit 1; }
storage_args+=(--blob-name registration.lock)
lease_id=''
for attempt in {1..120}; do
    if lease_id=$(az storage blob lease acquire "${storage_args[@]}" --lease-duration 60 --output tsv 2>/dev/null); then
        break
    fi
    sleep 5
done
[[ -n "$lease_id" ]] || { echo 'Timed out waiting for the AVD registration lease' >&2; exit 1; }
parent_pid=$$
(
    while sleep 15; do
        az storage blob lease renew "${storage_args[@]}" --lease-id "$lease_id" --output none >/dev/null 2>&1 || { kill -TERM "$parent_pid"; exit 1; }
    done
) &
renew_pid=$!
cleanup() {
    kill "$renew_pid" 2>/dev/null || true
    wait "$renew_pid" 2>/dev/null || true
    az storage blob lease release "${storage_args[@]}" --lease-id "$lease_id" --output none >/dev/null 2>&1 || true
}
trap cleanup EXIT
trap 'exit 1' TERM INT

management_token=$(curl --fail --silent --show-error --max-time 30 -H Metadata:true "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https%3A%2F%2Fmanagement.azure.com%2F&client_id=$RP_CLIENT_ID" | jq -er .access_token)
token_url="https://management.azure.com$HOST_POOL_ID/retrieveRegistrationToken?api-version=2024-04-03"
response=$(curl --silent --show-error --max-time 60 --request POST --header "Authorization: Bearer $management_token" --data '' --write-out '%{http_code}' "$token_url")
status=${response: -3}
registration=${response::-3}
if [[ "$status" == 404 ]]; then
    registration='{}'
elif [[ "$status" != 200 ]]; then
    echo "Unable to retrieve AVD registration credentials (HTTP $status)" >&2
    exit 1
fi
expiry=$(jq -r '.expirationTime // empty' <<< "$registration")
expiry_epoch=0
if [[ -n "$expiry" ]]; then expiry_epoch=$(date -u -d "$expiry" +%s); fi
if [[ "$expiry_epoch" -lt $(($(date -u +%s) + 14400)) ]] || [[ -z $(jq -r '.token // empty' <<< "$registration") ]]; then
    body=$(jq -cn --arg expiry "$(date -u -d '+24 hours' '+%Y-%m-%dT%H:%M:%SZ')" '{properties:{registrationInfo:{expirationTime:$expiry,registrationTokenOperation:"Update"}}}')
    az rest --method patch --url "https://management.azure.com$HOST_POOL_ID?api-version=2024-04-03" --body "$body" --output none
    registration=$(az rest --method post --url "$token_url" --output json)
fi
registration_token=$(jq -er '.token | select(length > 0)' <<< "$registration")
az storage blob lease renew "${storage_args[@]}" --lease-id "$lease_id" --output none
az keyvault secret set --vault-name "$KEY_VAULT_NAME" --name "$SECRET_NAME" --value "$registration_token" --output none --only-show-errors