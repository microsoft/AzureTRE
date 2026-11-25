#!/bin/bash
# The Dockerfile runs this script at each start. The web app sends its output to Log Analytics.

# Gitea prints the full command line when a command fails, so hide the secrets in its output.
gitea_cli() {
    local output status secret
    output=$(gitea "$@" 2>&1)
    status=$?
    for secret in "$GITEA_PASSWD" "${GITEA__database__PASSWD:-}"; do
        if [ -n "$secret" ]; then
            output=${output//"$secret"/"***"}
        fi
    done
    if [ -n "$output" ]; then
        printf '%s\n' "$output"
    fi
    return "$status"
}

while [[ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/swagger)" != @("200"|"302") ]]; do
    echo "Waiting for web service"
    sleep 5
done

# If App Service cannot read a Key Vault reference, the value is the reference text. Do not store it in Gitea.
if [[ -z "$GITEA_PASSWD" || "$GITEA_PASSWD" == @Microsoft.KeyVault* ]]; then
    echo "The value of GITEA_PASSWD is missing or its Key Vault reference is not resolved"
    exit 1
fi

echo "Adding admin user"
if gitea_cli admin user list --admin | awk 'NR > 1 { print $2 }' | grep -qxF "$GITEA_USERNAME"; then
    echo "The admin user exists"
else
    # Do not add --access-token. Gitea prints the new token.
    gitea_cli admin user create --admin --username="$GITEA_USERNAME" --password="$GITEA_PASSWD" --email="$GITEA_EMAIL" --must-change-password=false
fi
