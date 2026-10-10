#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

export PGCONNECT_TIMEOUT=30
export PGOPTIONS='-c statement_timeout=600000 -c lock_timeout=30000'

# Retry only the unauthenticated readiness request. Failed logins can lock accounts.
info_file=$(mktemp)
trap 'rm -f "$info_file"' EXIT
# Expand readiness variables inside the bounded child shell.
# shellcheck disable=SC2016
WEB_API_INFO_FILE="$info_file" timeout 600 bash -eu -o pipefail -c '
    until curl "${WEB_API_URL%/}/info" --fail --silent --show-error \
        --connect-timeout 5 --max-time 15 --output "$WEB_API_INFO_FILE" &&
        jq -e --arg version "$WEB_API_VERSION" ".version == \$version" "$WEB_API_INFO_FILE" > /dev/null; do
        sleep 10
    done
'

psql -X -v ON_ERROR_STOP=1 "$OHDSI_ADMIN_CONNECTION_STRING" -f ../sql/atlas_create_security.sql
psql -X -v ON_ERROR_STOP=1 "$OHDSI_ADMIN_CONNECTION_STRING" -f ../sql/atlas_default_roles.sql

IFS=',' read -r -a users <<< "$ATLAS_USERS"
if (( ${#users[@]} == 0 || ${#users[@]} % 2 != 0 )); then
    printf 'ATLAS_USERS must contain username and password pairs\n' >&2
    exit 1
fi
for ((index=0; index<${#users[@]}; index+=2)); do
    username=${users[index]}
    password=${users[index+1]}
    # shellcheck disable=SC2016
    atlaspw=$(htpasswd -bnBC 4 "" "$password" | tr -d ':\n' | sed 's/$2y/$2a/')
    psql -X -v ON_ERROR_STOP=1 "$OHDSI_ADMIN_CONNECTION_STRING" \
        -v "username=$username" -v "password_hash=$atlaspw" <<'SQL'
INSERT INTO webapi_security.security (email, password) VALUES (:'username', :'password_hash');
SQL
    # The response can contain an authentication token. Do not write it to the log.
    curl "${WEB_API_URL%/}/user/login/db" --fail --silent --show-error \
        --connect-timeout 5 --max-time 30 --output /dev/null \
        --data-urlencode "login=$username" --data-urlencode "password=$password"

    role_id=10
    if (( index == 0 )); then role_id=2; fi
    psql -X -v ON_ERROR_STOP=1 "$OHDSI_ADMIN_CONNECTION_STRING" \
        -v "username=$username" -v "role_id=$role_id" <<'SQL'
INSERT INTO webapi.sec_user_role (user_id, role_id)
SELECT id, :'role_id'::integer FROM webapi.sec_user u WHERE login = :'username'
AND NOT EXISTS (SELECT FROM webapi.sec_user_role r WHERE r.user_id = u.id AND r.role_id = :'role_id'::integer);
SELECT EXISTS (
    SELECT FROM webapi.sec_user u JOIN webapi.sec_user_role r ON r.user_id = u.id
    WHERE u.login = :'username' AND r.role_id = :'role_id'::integer
) AS role_assigned \gset
\if :role_assigned
\else
    DO $$ BEGIN RAISE EXCEPTION 'Application user role assignment failed'; END $$;
\endif
SQL
done
