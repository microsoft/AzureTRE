#!/bin/bash

while [[ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/api/swagger)" != @("200"|"302") ]]; do
    echo "Waiting for web service"
    sleep 5
done

if [ -z "$GITEA_USERNAME" ]; then
    echo "Gitea username is not set"
    s6-svc -k /etc/s6/gitea
    sleep 60
fi

# The admin commands contain secrets. The script hides them in the Gitea output.
su gitea -s /bin/bash -c "bash /configure_gitea_admin.sh"
