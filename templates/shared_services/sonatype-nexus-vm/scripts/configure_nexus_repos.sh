#!/bin/bash
set -o pipefail
set -o nounset
shopt -s nullglob
# set -o xtrace

VAULT_NAME="${1:-}"
MSI_CLIENT_ID="${2:-}"

if [ -z "$VAULT_NAME" ]; then
  echo 'ERROR - VAULT_NAME (arg 1) must be provided'
  exit 1
fi

if [ -z "$MSI_CLIENT_ID" ]; then
  echo 'ERROR - MSI_CLIENT_ID (arg 2) must be provided'
  exit 1
fi

# Fetch the Nexus admin password from Key Vault using the VM's managed identity via IMDS.
# HTTP to link-local address bypasses firewall; Key Vault is reached over its private endpoint.
echo "Fetching Nexus admin password from Key Vault '${VAULT_NAME}'..."
KV_TOKEN=$(curl -s -H 'Metadata:true' \
  "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&client_id=${MSI_CLIENT_ID}&resource=https://vault.azure.net" \
  | jq -r '.access_token')
if [ -z "$KV_TOKEN" ] || [ "$KV_TOKEN" = "null" ]; then
  echo "ERROR - Failed to get Key Vault access token from IMDS"
  exit 1
fi

NEXUS_ADMIN_PASSWORD=$(curl -s \
  -H "Authorization: Bearer ${KV_TOKEN}" \
  "https://${VAULT_NAME}.vault.azure.net/secrets/nexus-admin-password?api-version=7.4" \
  | jq -r '.value')
if [ -z "$NEXUS_ADMIN_PASSWORD" ] || [ "$NEXUS_ADMIN_PASSWORD" = "null" ]; then
  echo "ERROR - Failed to fetch nexus-admin-password from Key Vault '${VAULT_NAME}'"
  exit 1
fi
echo "Successfully fetched Nexus admin password from Key Vault."

retry_with_backoff() {
  local func="$1"
  shift
  local sleep_time=10
  local max_sleep=180

  while [ "$sleep_time" -lt "$max_sleep" ]; do
    if "$func" "$@"; then
      return 0
    fi
    sleep "$sleep_time"
    sleep_time=$((sleep_time * 2))
  done
  return 1
}

check_repos_config() {
  [ -d "$(dirname "${BASH_SOURCE[0]}")/nexus_repos_config" ]
}

echo 'Checking for ./nexus_repos_config directory...'
if ! retry_with_backoff check_repos_config; then
  echo 'ERROR - Timeout while waiting for nexus_repos_config directory'
  exit 1
fi

nexus_ready() {
  curl -s http://localhost/service/rest/v1/status -k > /dev/null
}

echo 'Waiting for Nexus service to be fully available...'
if ! retry_with_backoff nexus_ready; then
  echo 'ERROR - Timeout while waiting for Nexus to be available'
  exit 1
fi

# Accept Community Edition EULA (required for Nexus 3.77+)
echo "Checking Community Edition EULA status..."
eula_response=$(curl -s -u admin:"$NEXUS_ADMIN_PASSWORD" \
  'http://localhost/service/rest/v1/system/eula' \
  -H 'accept: application/json' \
  -k 2>/dev/null)

if echo "$eula_response" | jq -e '.accepted == false' > /dev/null 2>&1; then
  echo "EULA not yet accepted. Accepting now..."
  # Extract disclaimer and build proper JSON using jq to handle escaping
  disclaimer=$(echo "$eula_response" | jq -r '.disclaimer')
  eula_payload=$(jq -n --arg disc "$disclaimer" '{"disclaimer": $disc, "accepted": true}')
  eula_status_code=$(curl -s -u admin:"$NEXUS_ADMIN_PASSWORD" -X POST \
    'http://localhost/service/rest/v1/system/eula' \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d "$eula_payload" \
    -k -w "%{http_code}" -o /dev/null)
  if [ "$eula_status_code" -eq 204 ]; then
    echo "EULA accepted successfully."
  else
    echo "WARNING - Failed to accept EULA (HTTP $eula_status_code). This may cause repository access issues."
  fi
elif echo "$eula_response" | jq -e '.accepted == true' > /dev/null 2>&1; then
  echo "EULA already accepted."
else
  echo "EULA endpoint not available (older Nexus version or Pro edition). Skipping."
fi

echo "Getting current anonymous settings in Nexus..."
current_anon_json=$(curl -iu admin:"$NEXUS_ADMIN_PASSWORD" -X GET \
  'http://localhost/service/rest/v1/security/anonymous' \
  -H 'accept: application/json' \
  -k -s)
echo "Current anonymous settings: $current_anon_json"

echo "Enabling anonymous access in Nexus..."
anon_status_code=$(curl -iu admin:"$NEXUS_ADMIN_PASSWORD" -X PUT \
  'http://localhost/service/rest/v1/security/anonymous' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{"enabled": true}' \
  -k -s -w "%{http_code}" -o /dev/null)
echo "Response received from Nexus for enabling anonymous access: $anon_status_code"
if [ "$anon_status_code" -ne 200 ]; then
    echo "ERROR - Failed to enable anonymous access."
    exit 1
fi

echo "Configuring Nexus repositories..."
# Create or update a proxy for each .json file so modified configurations are
# applied to an existing Nexus instance without needing to recreate it.
for filename in "$(dirname "${BASH_SOURCE[0]}")"/nexus_repos_config/*.json; do
    echo "Found config file: $filename. Sending to Nexus..."
    base_type=$( jq .baseType "$filename" | sed 's/"//g')
    repo_type=$( jq .repoType "$filename" | sed 's/"//g')
    repo_name=$( jq .name "$filename" | sed 's/"//g')
    create_url="http://localhost/service/rest/v1/repositories/$base_type/$repo_type"
    update_url="$create_url/$repo_name"

    configure_repo() {
      local file="$1"
      local create="$2"
      local update="$3"
      local pass="$4"
      local response code body
      # Try to create the repository first.
      response=$(curl -u admin:"$pass" -XPOST \
        "$create" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$file" \
        -k -s -w $'\n%{http_code}')
      code=${response##*$'\n'}
      body=${response%$'\n'*}
      echo "Response received from Nexus when creating repository: $code"
      if [ "$code" -eq 201 ]; then
        return 0
      fi
      # If it already exists, update it so configuration changes are applied.
      code=$(curl -iu admin:"$pass" -XPUT \
        "$update" \
        -H 'accept: application/json' \
        -H 'Content-Type: application/json' \
        -d @"$file" \
        -k -s -w "%{http_code}" -o /dev/null)
      echo "Response received from Nexus when updating repository: $code"
      if [ "$code" -eq 200 ] || [ "$code" -eq 202 ] || [ "$code" -eq 204 ]; then
        return 0
      fi
      # A proxy repo whose remoteUrl no longer resolves fails Nexus 3.94+ restore
      # validation, leaving it in a failed state: the name is reserved (create
      # returns "Name is already used") but it cannot be updated (404). It can't
      # be reconciled via the API, so warn and skip rather than blocking the whole
      # upgrade on an already-broken repository.
      if [ "$code" -eq 404 ] && printf '%s' "$body" | grep -qi 'already used'; then
        echo "WARNING - Repository $repo_name is in a failed state in Nexus and cannot be updated (its proxy remote URL may be unreachable). Skipping."
        return 0
      fi
      return 1
    }

    if ! retry_with_backoff configure_repo "$filename" "$create_url" "$update_url" "$NEXUS_ADMIN_PASSWORD"; then
      echo "ERROR - Timeout while trying to configure $repo_name"
      exit 1
    fi
done

echo 'Configuring realms...'
status_code=$(curl -iu admin:"$NEXUS_ADMIN_PASSWORD" -XPUT \
  'http://localhost/service/rest/v1/security/realms/active' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d @"$(dirname "${BASH_SOURCE[0]}")"/nexus_realms_config.json \
  -k -s -w "%{http_code}" -o /dev/null)
echo "Response received from Nexus: $status_code"
