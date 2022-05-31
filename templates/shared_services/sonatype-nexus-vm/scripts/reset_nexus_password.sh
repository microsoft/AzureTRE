#!/bin/bash
set -o pipefail
set -o nounset
# set -o xtrace

if [ -z "$1" ]
  then
    echo 'New password to set needs to be passed as argument'
fi

# Get the current password so we can post to the API
# (this is created in /nexus-data mounted volume as part of Nexus container start-up)
password_timeout=300
echo 'Checking for Nexus admin password file...'
while [ ! -f /etc/nexus-data/admin.password ]; do
  # We must first wait for the file to be created
  if [ $password_timeout == 0 ]; then
    echo 'ERROR - Timeout while waiting for nexus-data/admin.password to be created'
    exit 1
  fi
  sleep 1
  ((password_timeout--))
done
current_password=$(cat /etc/nexus-data/admin.password)

# Set own admin password so we can connect to repository manager later on using TF KV secret
reset_timeout=300
echo "Nexus default admin password found ($current_password). Resetting..."
res=1
while test "$res" != "0"; do
  curl -ifu admin:"$current_password" -XPUT -H 'Content-Type:text/plain' --data "$1" \
    http://localhost/service/rest/v1/security/users/admin/change-password
  res=$?
  echo "Attempt to reset password finished with code $res"
  if test "$res" == "0"; then
    echo 'Password reset successfully.'
  else
    if [ $reset_timeout == 0 ]; then
      echo 'ERROR - Timeout while trying to reset Nexus admin password'
      exit 1
    fi
    sleep 5
    ((reset_timeout+=5))
  fi
done
