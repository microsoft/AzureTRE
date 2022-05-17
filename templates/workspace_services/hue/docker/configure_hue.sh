#!/bin/bash

while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' http://localhost:3000/api/swagger)" != @("200"|"302") ]]; do
    echo "Waiting for web service"
    sleep 5
done

if [ -z $HUE_USERNAME ]; then
    echo "Hue username is not set"
    s6-svc -k /etc/s6/hue
    sleep 60
fi

echo "Adding admin user"
echo "HUE admin user create --admin --access-token --username='${HUE_USERNAME}' --password='${HUE_PASSWD}' --email='${HUE_EMAIL}' --must-change-password=false"
su HUE -c "HUE admin user create --admin --access-token --username='${HUE_USERNAME}' --password='${HUE_PASSWD}' --email='${HUE_EMAIL}' --must-change-password=false"

echo "Configuring OIDC"
echo "hue admin auth add-oauth --name oidc --provider openidConnect --key '${HUE_OPENID_CLIENT_ID}' --secret '${HUE_OPENID_CLIENT_SECRET}' --auto-discover-url '${HUE_OPENID_AUTHORITY}/.well-known/openid-configuration' --group-claim-name 'roles' --admin-group 'WorkspaceOwner'"
su HUE -c "HUE admin auth add-oauth --name oidc --provider openidConnect --key '${HUE_OPENID_CLIENT_ID}' --secret '${HUE_OPENID_CLIENT_SECRET}' --auto-discover-url '${HUE_OPENID_AUTHORITY}/.well-known/openid-configuration' --group-claim-name 'roles' --admin-group 'WorkspaceOwner'"
