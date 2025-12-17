#!/bin/bash
# Script to fetch user details from Azure AD with graceful fallback
# Returns either the friendly username or a generated fallback

set -e

# Read JSON input from Terraform
eval "$(jq -r '@sh "OWNER_ID=\(.owner_id) TENANT_ID=\(.tenant_id) CLIENT_ID=\(.client_id) CLIENT_SECRET=\(.client_secret)"')"

# Fallback username (last 20 chars of owner_id without dashes)
FALLBACK_USERNAME=$(echo "$OWNER_ID" | tr -d '-' | tail -c 21)

# Try to get access token
if ! ACCESS_TOKEN=$(curl -sf -X POST "https://login.microsoftonline.com/$TENANT_ID/oauth2/v2.0/token" \
  -d "client_id=$CLIENT_ID" \
  -d "client_secret=$CLIENT_SECRET" \
  -d "scope=https://graph.microsoft.com/.default" \
  -d "grant_type=client_credentials" 2>/dev/null | jq -r '.access_token // empty'); then
  # Failed to get token, use fallback
  jq -n --arg username "$FALLBACK_USERNAME" '{"username":$username}'
  exit 0
fi

# Try to fetch user details
if ! USER_DATA=$(curl -sf -H "Authorization: Bearer $ACCESS_TOKEN" \
  "https://graph.microsoft.com/v1.0/users/$OWNER_ID" 2>/dev/null); then
  # User doesn't exist or API failed, use fallback
  jq -n --arg username "$FALLBACK_USERNAME" '{"username":$username}'
  exit 0
fi

# Extract username from email or UPN
MAIL=$(echo "$USER_DATA" | jq -r '.mail // empty')
UPN=$(echo "$USER_DATA" | jq -r '.userPrincipalName // empty')

if [ -n "$MAIL" ] && echo "$UPN" | grep -q "#EXT#"; then
  # External user with mail: use email prefix
  USERNAME=$(echo "$MAIL" | cut -d'@' -f1 | head -c 20)
else
  # Regular user: use UPN prefix
  USERNAME=$(echo "$UPN" | cut -d'@' -f1 | cut -d'#' -f1 | head -c 20)
fi

# Return the friendly username
jq -n --arg username "$USERNAME" '{"username":$username}'
