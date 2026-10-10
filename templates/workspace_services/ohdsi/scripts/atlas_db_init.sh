#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

export PGCONNECT_TIMEOUT=30
export PGOPTIONS='-c statement_timeout=600000 -c lock_timeout=30000'

printf 'Creating roles and users\n'
psql -X -v ON_ERROR_STOP=1 "$MAIN_CONNECTION_STRING" \
    -v "admin_role=$OHDSI_ADMIN_ROLE" -v "app_role=$OHDSI_APP_ROLE" \
    -v "admin_username=$OHDSI_ADMIN_USERNAME" -v "app_username=$OHDSI_APP_USERNAME" \
    -v "admin_password=$OHDSI_ADMIN_PASSWORD" -v "app_password=$OHDSI_APP_PASSWORD" \
    -v "database_name=$DATABASE_NAME" -f ../sql/atlas_create_roles_users.sql

printf 'Creating schema\n'
psql -X -v ON_ERROR_STOP=1 "$OHDSI_ADMIN_CONNECTION_STRING" \
    -v "schema_name=$SCHEMA_NAME" -v "admin_role=$OHDSI_ADMIN_ROLE" \
    -v "app_role=$OHDSI_APP_ROLE" -f ../sql/atlas_create_schema.sql
printf 'Database initialisation complete\n'
