#!/bin/bash
set -e

echo $(env)

script_dir=$(realpath $(dirname "${BASH_SOURCE[0]}"))

if [[ -z ${STORAGE_ACCOUNT} ]]; then
  echo "STORAGE_ACCOUNT not set"
  exit 1
fi

IPADDR=$(curl ipecho.net/plain; echo)

# The storage account is protected by network rules
# The rules need to be temporarily lifted so that the index.html file, if required, and certificate can be uploaded
echo "Creating network rule on storage account ${STORAGE_ACCOUNT} for $IPADDR"
az storage account network-rule add --account-name "${STORAGE_ACCOUNT}" --ip-address $IPADDR
echo "Waiting for network rule to take effect"
sleep 30s
echo "Created network rule on storage account"

echo "Checking for index.html file in storage account"

# Create the default index.html page
cat << EOF > index.html
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"><head><meta charset="utf-8"/><title></title></head><body></body></html>
EOF

indexExists=$(az storage blob list -o json \
    --account-name "${STORAGE_ACCOUNT}" \
    --auth-mode login \
    --container-name '$web' \
    --query "[?name=='index.html'].name" \
    | jq 'length')

if [[ ${indexExists} -lt 1 ]]; then
    echo "Uploading index.html file"

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

# Initiate the ACME challange
/opt/certbot/bin/certbot certonly \
    --config-dir ${ledir} \
    --work-dir ${ledir} \
    --logs-dir ${ledir}/logs \
    --manual \
    --preferred-challenges=http \
    --manual-auth-hook ${script_dir}/auth-hook.sh \
    --manual-cleanup-hook ${script_dir}/cleanup-hook.sh \
    --domain $FQDN \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email

# Convert the generated certificate to a .pfx
CERT_DIR="${ledir}/live/$FQDN"
CERT_PASSWORD=$(openssl rand -base64 30)
openssl pkcs12 -export \
    -inkey "${CERT_DIR}/privkey.pem" \
    -in "${CERT_DIR}/fullchain.pem" \
    -out "${CERT_DIR}/aci.pfx" \
    -passout "pass:${CERT_PASSWORD}"

if [[ -n ${KEYVAULT} ]]; then
    sid=$(az keyvault certificate import \
        -o json \
        --vault-name ${KEYVAULT} \
        --name 'letsencrypt' \
        --file "${CERT_DIR}/aci.pfx" \
        --password "${CERT_PASSWORD}" \
        | jq -r '.sid')

    az network application-gateway ssl-cert update \
        --resource-group "${RESOURCE_GROUP}" \
        --gateway-name "${APPLICATION_GATEWAY}" \
        --name 'cert-primary' \
        --key-vault-secret-id "${sid}"
else
    az network application-gateway ssl-cert update \
        --resource-group "${RESOURCE_GROUP}" \
        --gateway-name "${APPLICATION_GATEWAY}" \
        --name 'letsencrypt' \
        --cert-file "${CERT_DIR}/aci.pfx" \
        --cert-password "${CERT_PASSWORD}"
fi

echo "Removing network rule on storage account"
az storage account network-rule remove --account-name ${STORAGE_ACCOUNT} --ip-address ${IPADDR}
echo "Removed network rule on storage account"
