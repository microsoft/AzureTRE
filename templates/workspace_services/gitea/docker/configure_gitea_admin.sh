#!/bin/bash
# configure_gitea.sh runs this script as the gitea user. The web app sends its output to Log Analytics.

# Gitea prints the full command line when a command fails, so hide the secrets in its output.
gitea_cli() {
    local output status secret
    output=$(gitea "$@" 2>&1)
    status=$?
    for secret in "$GITEA_PASSWD" "$GITEA_OPENID_CLIENT_SECRET" "${GITEA__database__PASSWD:-}"; do
        if [ -n "$secret" ]; then
            output=${output//"$secret"/"***"}
        fi
    done
    if [ -n "$output" ]; then
        printf '%s\n' "$output"
    fi
    return "$status"
}

echo "Adding admin user"
if gitea_cli admin user list --admin | awk 'NR > 1 { print $2 }' | grep -qxF "$GITEA_USERNAME"; then
    echo "The admin user exists"
else
    gitea_cli admin user create --admin --username="$GITEA_USERNAME" --password="$GITEA_PASSWD" --email="$GITEA_EMAIL" --must-change-password=false
fi

echo "Configuring OIDC"
oidc=(--name oidc --provider openidConnect --key "$GITEA_OPENID_CLIENT_ID" --secret "$GITEA_OPENID_CLIENT_SECRET"
    --auto-discover-url "$GITEA_OPENID_AUTHORITY/.well-known/openid-configuration" --group-claim-name roles --admin-group WorkspaceOwner)
source_id=$(gitea_cli admin auth list | awk '$2 == "oidc" { print $1 }')
# Update an existing source, so that it gets the current values, for example a new client secret.
if [ -z "$source_id" ]; then
    gitea_cli admin auth add-oauth "${oidc[@]}"
else
    gitea_cli admin auth update-oauth --id "$source_id" "${oidc[@]}"
fi
