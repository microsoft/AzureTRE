#!/bin/bash
# configure_gitea.sh runs this script as the gitea user. The web app sends its output to Log Analytics.
# Exit status 10 means that the OIDC settings changed and that Gitea must restart to use them.

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

# If App Service cannot read a Key Vault reference, the value is the reference text. Do not store it in Gitea.
for name in GITEA_PASSWD GITEA_OPENID_CLIENT_SECRET; do
    if [[ -z "${!name}" || "${!name}" == @Microsoft.KeyVault* ]]; then
        echo "The value of $name is missing or its Key Vault reference is not resolved"
        exit 1
    fi
done

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
    gitea_cli admin auth add-oauth "${oidc[@]}" || exit
else
    gitea_cli admin auth update-oauth --id "$source_id" "${oidc[@]}" || exit
fi

# The running Gitea keeps the OIDC settings of an existing source from its start. It loads a new source when it needs it.
# The file share keeps a hash of the settings, so that the script can find a change.
hash_file="${GITEA_CUSTOM:-/data/gitea}/oidc-settings.sha256"
hash=$(printf '%s\n' "${oidc[@]}" | sha256sum | cut -d ' ' -f 1)
if [ -n "$source_id" ] && [ "$hash" != "$(cat "$hash_file" 2>/dev/null)" ]; then
    changed=true
fi
# Request a restart only if the hash is stored. Otherwise each start requests a restart again.
if printf '%s\n' "$hash" > "$hash_file" && [ "$changed" = true ]; then
    exit 10
fi
