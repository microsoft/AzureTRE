#!/bin/bash

cat << EOF > 'validation.txt'
${CERTBOT_VALIDATION}
EOF

# shellcheck disable=SC2016
az storage blob upload \
    --account-name "${STORAGE_ACCOUNT_NAME}" \
    --auth-mode login \
    --container-name '$web' \
    --file 'validation.txt' \
    --name ".well-known/acme-challenge/${CERTBOT_TOKEN}" \
    --no-progress \
    --only-show-errors

sleep 10s
