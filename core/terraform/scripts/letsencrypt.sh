#!/bin/bash
set -e

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

if [[ -z ${STORAGE_ACCOUNT} ]]; then
  echo "STORAGE_ACCOUNT not set"
  exit 1
fi

# The storage account is protected by network rules
#
# The rules need to be temporarily lifted so that the script can determine if the index.html file
# already exists and, if not, create it. The firewall rules also need lifting so that the
# certificate can be uploaded.
#
# By default, this process adds the IP address of the machine running this script to the allow-list
# of the storage account network rules. In some situations this approach may not work. For example,
# where the machine running this script (an AzDo build agent, for example), and the storage account
# are both on the same private network, and the public IP of the machine running the script is never
# used. In this situation, you may need to drop the default Deny rule.
#
# If the environment variable LETSENCRYPT_DROP_ALL_RULES=1 is set then this script will drop the
# default Deny rule, and then re-enable it once the script is complete, rather add the IP address
# to the allow rules.

if  [[ "${LETSENCRYPT_DROP_ALL_RULES}" == "1" ]]; then

  echo "Removing default DENY rule on storage account ${STORAGE_ACCOUNT}"
  az storage account update \
    --default-action Allow \
    --name "${STORAGE_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP_NAME}"

else

  if [[ -z ${PUBLIC_DEPLOYMENT_IP_ADDRESS:-} ]]; then
    IPADDR=$(curl ipecho.net/plain; echo)
  else
    IPADDR=${PUBLIC_DEPLOYMENT_IP_ADDRESS}
  fi

  echo "Creating network rule on storage account ${STORAGE_ACCOUNT} for $IPADDR"
  az storage account network-rule add \
    --account-name "${STORAGE_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --ip-address "$IPADDR"

fi

echo "Waiting for network rule to take effect"
sleep 30s
echo "Created network rule on storage account"

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

# Initiate the ACME challange
/opt/certbot/bin/certbot certonly \
    --config-dir "${ledir}" \
    --work-dir "${ledir}" \
    --logs-dir "${ledir}"/logs \
    --manual \
    --preferred-challenges=http \
    --manual-auth-hook "${script_dir}"/auth-hook.sh \
    --manual-cleanup-hook "${script_dir}"/cleanup-hook.sh \
    --domain "$FQDN" \
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

if  [[ "${LETSENCRYPT_DROP_ALL_RULES}" == "1" ]]; then

  echo "Resetting the default DENY rule on storage account ${STORAGE_ACCOUNT}"
  az storage account update \
    --default-action Deny \
    --name "${STORAGE_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP_NAME}"

else

  echo "Ressetting network rule on storage account (removing $IPADDR from allow list)"
  az storage account network-rule remove \
    --account-name "${STORAGE_ACCOUNT}" \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --ip-address "${IPADDR}"

fi
