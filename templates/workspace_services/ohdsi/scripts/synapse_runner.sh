#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

export SQLCMDPASSWORD="${ADMIN_USER_PASSWORD}"

printf 'Initializing Results and Temp schemas'
sqlcmd -U "${ADMIN_USERNAME}" -S "${SYNAPSE_SERVER}" -d "${SYNAPSE_DATABASE}" -W -v RESULTS_SCHEMA_NAME="${RESULTS_SCHEMA_NAME}" -v TEMP_SCHEMA_NAME="${TEMP_SCHEMA_NAME}" -v ORIGIN_RESULTS_SCHEMA_NAME="${ORIGIN_RESULTS_SCHEMA_NAME}" -i "${SQL_FILE_PATH}"
printf 'Initializing Results and Temp schemas: done.'

printf 'Done'
