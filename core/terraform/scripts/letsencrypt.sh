#!/bin/bash
set -e

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

if [[ -z ${STORAGE_ACCOUNT} ]]; then
  echo "STORAGE_ACCOUNT not set"
  exit 1
fi

if [[ -n ${KEYVAULT} ]]; then
  # shellcheck disable=SC1091
  source "$script_dir/../../../devops/scripts/kv_add_network_exception.sh"
fi

# The storage account is protected by network rules
#
# The rules need to be temporarily lifted so that the script can determine if the index.html file
# already exists and, if not, create it. The firewall rules also need lifting so that the
# certificate can be uploaded.
#
# shellcheck disable=SC1091
source "$script_dir/../../../devops/scripts/storage_enable_public_access.sh" \
  --storage-account-name "${STORAGE_ACCOUNT}" \
  --resource-group-name "${RESOURCE_GROUP_NAME}"

echo "Waiting for network rule to take effect"
sleep 30s
echo "Storage account network access configured"

echo "Checking for index.html file in storage account"

# Create the default index.html page
cat << EOF > index.html
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"><head><meta charset="utf-8"/><title></title></head><body></body></html>
EOF

# shellcheck disable=SC2016
indexExists=$(az storage blob list -o json \
    --account-name "${STORAGE_ACCOUNT}" \
    --auth-mode login \
    --container-name '$web' \
    --query "[?name=='index.html'].name" \
    | jq 'length')

if [[ ${indexExists} -lt 1 ]]; then
    echo "Uploading index.html file"

    # shellcheck disable=SC2016
    az storage blob upload \
        --account-name "${STORAGE_ACCOUNT}" \
        --auth-mode login \
        --container-name '$web' \
        --file index.html \
        --name index.html \
        --no-progress \
        --only-show-errors

    # Wait a bit for the App Gateway health probe to notice
    echo "Waiting 30s for health probe"
    sleep 30s
else
    echo "index.html already present"
fi

ledir=$(pwd)/letsencrypt

mkdir -p "${ledir}/logs"

CERT_FQDN=$FQDN
if [[ -n "$CUSTOM_DOMAIN" ]]; then
  CERT_FQDN=$CUSTOM_DOMAIN
fi

echo "Requesting certificate for $CERT_FQDN..."

# Initiate the ACME challange
/opt/certbot/bin/certbot certonly \
    --config-dir "${ledir}" \
    --work-dir "${ledir}" \
    --logs-dir "${ledir}"/logs \
    --manual \
    --preferred-challenges=http \
    --manual-auth-hook "${script_dir}"/auth-hook.sh \
    --manual-cleanup-hook "${script_dir}"/cleanup-hook.sh \
    --domain "$CERT_FQDN" \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email

# Convert the generated certificate to a .pfx
CERT_DIR="${ledir}/live/$CERT_FQDN"
CERT_PASSWORD=$(openssl rand -base64 30)
openssl pkcs12 -export \
    -inkey "${CERT_DIR}/privkey.pem" \
    -in "${CERT_DIR}/fullchain.pem" \
    -out "${CERT_DIR}/aci.pfx" \
    -passout "pass:${CERT_PASSWORD}"

if [[ -n ${KEYVAULT} ]]; then
    sid=$(az keyvault certificate import \
        -o json \
        --vault-name "${KEYVAULT}" \
        --name 'letsencrypt' \
        --file "${CERT_DIR}/aci.pfx" \
        --password "${CERT_PASSWORD}" \
        | jq -r '.sid')

    az network application-gateway ssl-cert update \
        --resource-group "${RESOURCE_GROUP_NAME}" \
        --gateway-name "${APPLICATION_GATEWAY}" \
        --name 'cert-primary' \
        --key-vault-secret-id "${sid}"
else
    az network application-gateway ssl-cert update \
        --resource-group "${RESOURCE_GROUP_NAME}" \
        --gateway-name "${APPLICATION_GATEWAY}" \
        --name 'letsencrypt' \
        --cert-file "${CERT_DIR}/aci.pfx" \
        --cert-password "${CERT_PASSWORD}"
fi

