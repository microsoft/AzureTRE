#!/bin/bash

while [[ "$(curl -s -o /dev/null -w ''%{http_code}'' http://localhost:3000/api/swagger)" != @("200"|"302") ]]; do
    echo "Waiting for web service"
    sleep 5
done

if [ -z $GITEA_USERNAME ]; then
    echo "Gitea username is not set"
    s6-svc -k /etc/s6/gitea
    sleep 60
fi

echo "Adding admin user"
echo "gitea admin user create --admin --access-token --username='${GITEA_USERNAME}' --password='${GITEA_PASSWD}' --email='${GITEA_EMAIL}' --must-change-password=false"
su gitea -c "gitea admin user create --admin --access-token --username='${GITEA_USERNAME}' --password='${GITEA_PASSWD}' --email='${GITEA_EMAIL}' --must-change-password=false"

# echo "Configuring OIDC"
# echo "gitea admin auth add-oauth --name oidc --provider openidConnect --key '${GITEA_OPENID_CLIENT_ID}' --secret '${GITEA_OPENID_CLIENT_SECRET}' --auto-discover-url '${GITEA_OPENID_AUTHORITY}/.well-known/openid-configuration' --group-claim-name 'roles' --admin-group 'WorkspaceOwner'"
# su gitea -c "gitea admin auth add-oauth --name oidc --provider openidConnect --key '${GITEA_OPENID_CLIENT_ID}' --secret '${GITEA_OPENID_CLIENT_SECRET}' --auto-discover-url '${GITEA_OPENID_AUTHORITY}/.well-known/openid-configuration' --group-claim-name 'roles' --admin-group 'WorkspaceOwner'"

# echo "Configuring Allowed Domains"
# CONFIG_FILE="/data/gitea/conf/app.ini"

# # Add the migrations section to the app.ini file if it doesn't exist
# if ! grep -q "\[migrations]" $CONFIG_FILE; then
# echo -e "\n[migrations]" >> $CONFIG_FILE
# fi
# # Add the allowed domains line to the migrations section
# if ! grep -q "ALLOWED_DOMAINS = $GITEA__ALLOWED_DOMAIN" $CONFIG_FILE; then
# echo -e "ALLOWED_DOMAINS = $GITEA__ALLOWED_DOMAIN" >> $CONFIG_FILE
# fi
