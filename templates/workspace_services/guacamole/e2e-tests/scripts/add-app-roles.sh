#!/usr/bin/env bash
# Script to add app roles to an existing Azure AD application
# Usage: ./add-app-roles.sh <app_id>

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <app_id>" >&2
  exit 1
fi

APP_ID="$1"

if ! command -v az >/dev/null 2>&1; then
  echo "Azure CLI (az) is required" >&2
  exit 1
fi

if ! az account show >/dev/null 2>&1; then
  echo "Run 'az login' before executing this script" >&2
  exit 1
fi

if ! command -v uuidgen >/dev/null 2>&1; then
  echo "Installing uuid-runtime package to provide uuidgen..."
  sudo apt-get update -qq
  sudo apt-get install -yqq uuid-runtime
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "Installing jq for JSON manipulation..."
  sudo apt-get update -qq
  sudo apt-get install -yqq jq
fi

echo "Adding app roles to Azure AD application ${APP_ID}..."

role_owner_id="$(uuidgen)"
role_researcher_id="$(uuidgen)"
role_airlock_id="$(uuidgen)"

roles_payload="$(jq -nc \
  --arg owner_id "${role_owner_id}" \
  --arg researcher_id "${role_researcher_id}" \
  --arg airlock_id "${role_airlock_id}" \
  '[
    {
      allowedMemberTypes: ["User"],
      description: "Workspace Owner role for Guacamole access",
      displayName: "WorkspaceOwner",
      id: $owner_id,
      isEnabled: true,
      value: "WorkspaceOwner"
    },
    {
      allowedMemberTypes: ["User"],
      description: "Workspace Researcher role for Guacamole access",
      displayName: "WorkspaceResearcher",
      id: $researcher_id,
      isEnabled: true,
      value: "WorkspaceResearcher"
    },
    {
      allowedMemberTypes: ["User"],
      description: "Airlock Manager role for Guacamole access",
      displayName: "AirlockManager",
      id: $airlock_id,
      isEnabled: true,
      value: "AirlockManager"
    }
  ]')"

az ad app update --id "${APP_ID}" --set "appRoles=${roles_payload}"

echo "Checking if service principal exists..."
sp_object_id="$(az ad sp list --filter "appId eq '${APP_ID}'" --query '[0].id' -o tsv)"

if [ -z "${sp_object_id}" ]; then
  echo "Creating service principal..."
  az ad sp create --id "${APP_ID}" >/dev/null
  sp_object_id="$(az ad sp show --id "${APP_ID}" --query id -o tsv)"
fi

echo "Assigning WorkspaceResearcher role to current user..."
current_user_id="$(az ad signed-in-user show --query id -o tsv)"

# Try to assign the role, ignore if already assigned
az rest --method POST \
  --uri "https://graph.microsoft.com/v1.0/servicePrincipals/${sp_object_id}/appRoleAssignedTo" \
  --headers "Content-Type=application/json" \
  --body "{
    \"principalId\": \"${current_user_id}\",
    \"resourceId\": \"${sp_object_id}\",
    \"appRoleId\": \"${role_researcher_id}\"
  }" 2>&1 | grep -v "already exists" || echo "✓ Role assignment complete"

cat <<EOF

Successfully configured app roles for ${APP_ID}:
  - WorkspaceOwner
  - WorkspaceResearcher
  - AirlockManager

Current user assigned: WorkspaceResearcher

IMPORTANT: Role assignments may take 5-10 minutes to propagate.
           Clear your browser cache and obtain a new token to include the 'roles' claim.
EOF
