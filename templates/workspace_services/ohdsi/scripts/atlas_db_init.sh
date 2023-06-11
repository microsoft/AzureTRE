#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

admin_user_password="${OHDSI_ADMIN_PASSWORD}${OHDSI_ADMIN_USERNAME}"
app_user_password="${OHDSI_APP_PASSWORD}${OHDSI_APP_USERNAME}"
admin_md5=("md5$(echo -n "$admin_user_password" | md5sum | awk '{ print $1 }')")
export admin_md5
app_md5=("md5$(echo -n "$app_user_password" | md5sum | awk '{ print $1 }')'")
export app_md5

printf 'Creating roles and users'
envsubst < ../sql/atlas_create_roles_users.sql | psql -v ON_ERROR_STOP=0 -e "$MAIN_CONNECTION_STRING"
printf 'Creating roles and users: done.'

printf 'Creating schema'
envsubst < ../sql/atlas_create_schema.sql | psql -v ON_ERROR_STOP=1 -e "$OHDSI_ADMIN_CONNECTION_STRING"
printf 'Creating schema: done.'

printf 'Done'
