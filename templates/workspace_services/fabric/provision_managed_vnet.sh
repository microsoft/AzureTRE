#!/bin/sh
set -e

# Triggers managed VNet provisioning for a Fabric workspace by running a
# temporary Spark notebook. The managed VNet provisions automatically when
# the first Spark session starts in a workspace with managed private endpoints.
#
# This is invoked from Terraform and MUST run BEFORE the workspace network
# communication policy denies outbound public access, otherwise Fabric's
# backend may not be able to complete VNet provisioning.
#
# Usage: provision_managed_vnet.sh <workspace_id>
# Requires: ARM_USE_MSI, ARM_TENANT_ID, ARM_CLIENT_ID, ARM_CLIENT_SECRET

WS_ID="${1:?Usage: provision_managed_vnet.sh <workspace_id>}"
API="https://api.fabric.microsoft.com/v1"
WS_API="${API}/workspaces/${WS_ID}"
NB_NAME="_vnet-init"

# ── Token ──────────────────────────────────────────────────────────────
if [ "${ARM_USE_MSI}" = "true" ]; then
  TOKEN=$(curl -s 'http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://api.fabric.microsoft.com' \
    -H 'Metadata: true' | jq -r '.access_token')
else
  TOKEN=$(curl -s -X POST \
    "https://login.microsoftonline.com/${ARM_TENANT_ID}/oauth2/v2.0/token" \
    -d "client_id=${ARM_CLIENT_ID}&client_secret=${ARM_CLIENT_SECRET}&scope=https://api.fabric.microsoft.com/.default&grant_type=client_credentials" \
    | jq -r '.access_token')
fi

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
  echo "ERROR: Failed to obtain Fabric API token"
  exit 1
fi

# ── Helper: delete notebook by ID (best-effort) ───────────────────────
cleanup() {
  if [ -n "$NB_ID" ] && [ "$NB_ID" != "null" ]; then
    echo "Cleaning up temporary notebook ${NB_ID}..."
    curl -s -o /dev/null -X DELETE \
      -H "Authorization: Bearer ${TOKEN}" \
      "${WS_API}/notebooks/${NB_ID}" 2>/dev/null || true
  fi
}

# ── Create temporary notebook ──────────────────────────────────────────
echo "Creating temporary notebook '${NB_NAME}' for VNet provisioning..."

IPYNB='{"nbformat":4,"nbformat_minor":5,"metadata":{"language_info":{"name":"python"}},"cells":[{"cell_type":"code","metadata":{},"source":["print(1)"],"outputs":[],"execution_count":null}]}'
NB_B64=$(printf '%s' "$IPYNB" | base64 -w 0)

HTTP=$(curl -s -o /tmp/nb_resp.json -D /tmp/nb_hdrs.txt -w '%{http_code}' \
  -X POST -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
  "${WS_API}/notebooks" \
  -d "{\"displayName\":\"${NB_NAME}\",\"definition\":{\"format\":\"ipynb\",\"parts\":[{\"path\":\"notebook-content.ipynb\",\"payload\":\"${NB_B64}\",\"payloadType\":\"InlineBase64\"}]}}")

NB_ID=""
if [ "$HTTP" = "201" ]; then
  NB_ID=$(jq -r '.id' /tmp/nb_resp.json)
elif [ "$HTTP" = "202" ]; then
  # Async creation – poll the operation URL
  OP_URL=$(grep -i '^location:' /tmp/nb_hdrs.txt | tr -d '\r' | sed 's/^[Ll]ocation:[[:space:]]*//')
  echo "  Notebook creation is async, polling..."
  for _ in $(seq 1 24); do
    sleep 5
    curl -s -o /tmp/op_resp.json -H "Authorization: Bearer ${TOKEN}" "${OP_URL}"
    OP_STATUS=$(jq -r '.status' /tmp/op_resp.json)
    if [ "$OP_STATUS" = "Succeeded" ]; then
      NB_ID=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${WS_API}/notebooks" \
        | jq -r ".value[] | select(.displayName==\"${NB_NAME}\") | .id")
      break
    elif [ "$OP_STATUS" = "Failed" ]; then
      echo "ERROR: Notebook creation failed"
      jq . /tmp/op_resp.json 2>/dev/null || true
      exit 1
    fi
  done
elif [ "$HTTP" = "409" ]; then
  # Notebook already exists from a previous run – reuse it
  echo "  Notebook already exists, reusing..."
  NB_ID=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${WS_API}/notebooks" \
    | jq -r ".value[] | select(.displayName==\"${NB_NAME}\") | .id")
else
  echo "ERROR: Notebook creation failed with HTTP ${HTTP}"
  cat /tmp/nb_resp.json 2>/dev/null || true
  exit 1
fi

if [ -z "$NB_ID" ] || [ "$NB_ID" = "null" ]; then
  echo "ERROR: Could not determine notebook ID"
  exit 1
fi

echo "  Notebook ID: ${NB_ID}"

# ── Run the notebook (triggers Spark session → VNet provisioning) ──────
echo "Running notebook to trigger Spark session and managed VNet provisioning..."
echo "  (First run with custom pool takes 3-5 minutes)"

HTTP=""
for ATTEMPT in 1 2 3; do
  HTTP=$(curl -s -o /tmp/job_resp.json -D /tmp/job_hdrs.txt -w '%{http_code}' \
    -X POST -H "Authorization: Bearer ${TOKEN}" \
    "${WS_API}/items/${NB_ID}/jobs/DefaultJob/instances")
  if [ "$HTTP" = "202" ]; then break; fi
  echo "  Attempt ${ATTEMPT}: HTTP ${HTTP}, retrying in 10s..."
  sleep 10
done

if [ "$HTTP" != "202" ]; then
  echo "ERROR: Failed to submit notebook job after 3 attempts (HTTP ${HTTP})"
  cat /tmp/job_resp.json 2>/dev/null || true
  cleanup
  exit 1
fi

JOB_URL=$(grep -i '^location:' /tmp/job_hdrs.txt | tr -d '\r' | sed 's/^[Ll]ocation:[[:space:]]*//')
echo "  Job submitted. Polling for completion..."

# ── Poll until complete (12 min timeout) ───────────────────────────────
MAX_WAIT=720
WAITED=0
INTERVAL=30

while [ "$WAITED" -lt "$MAX_WAIT" ]; do
  sleep ${INTERVAL}
  WAITED=$((WAITED + INTERVAL))
  curl -s -o /tmp/job_status.json -H "Authorization: Bearer ${TOKEN}" "${JOB_URL}"
  STATUS=$(jq -r '.status' /tmp/job_status.json)
  echo "  [${WAITED}s] Status: ${STATUS}"

  case "${STATUS}" in
    Completed)
      echo "Notebook completed – managed VNet provisioned successfully."
      break
      ;;
    Failed)
      echo "WARNING: Notebook job failed, but VNet was likely provisioned during Spark startup."
      jq -r '.failureReason // empty' /tmp/job_status.json 2>/dev/null || true
      break
      ;;
    Cancelled|Deduped)
      echo "WARNING: Job was ${STATUS}."
      break
      ;;
  esac
done

if [ "$WAITED" -ge "$MAX_WAIT" ]; then
  echo "WARNING: Timed out after ${MAX_WAIT}s. VNet may still be provisioning."
fi

# ── Cleanup ────────────────────────────────────────────────────────────
cleanup
echo "Managed VNet provisioning step complete."
