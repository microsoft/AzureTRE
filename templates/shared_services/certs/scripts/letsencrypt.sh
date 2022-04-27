#!/bin/bash
set -e

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

while [ "$1" != "" ]; do
    case $1 in
    --storage_account_name)
        shift
        storage_account_name=$1
        ;;
    --storage_account_id)
        shift
        storage_account_id=$1
        ;;
    --fqdn)
        shift
        fqdn=$1
        ;;
    --keyvault_name)
        shift
        keyvault_name=$1
        ;;
    --resource_group_name)
        shift
        resource_group_name=$1
        ;;
    --application_gateway_name)
        shift
        application_gateway_name=$1
        ;;
    --cert_name)
        shift
        cert_name=$1
        ;;
    *)
        echo "Unexpected argument: '$1'"
        usage
        ;;
    esac

    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi

    shift # remove the current value for `$1` and use the next
done

# done with processing args and can set this
set -o nounset

echo "Checking for index.html file in storage account"

# Assign Storage Blob Data Contributor permissions if not already present
objectId=$(az ad signed-in-user show --query objectId -o tsv)
az role assignment create --assignee "${objectId}" \
  --role "Storage Blob Data Contributor" \
  --scope "${storage_account_id}"

# Create the default index.html page
cat << EOF > index.html
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml"><head><meta charset="utf-8"/><title></title></head><body></body></html>
EOF

# shellcheck disable=SC2016
indexExists=$(az storage blob list -o json \
    --account-name "${storage_account_name}" \
    --auth-mode login \
    --container-name '$web' \
    --query "[?name=='index.html'].name" \
    | jq 'length')

if [[ ${indexExists} -lt 1 ]]; then
    echo "Uploading index.html file"

    # shellcheck disable=SC2016
    az storage blob upload \
        --account-name "${storage_account_name}" \
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

ledir="${script_dir}/../letsencrypt"
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
    --domain "${fqdn}" \
    --non-interactive \
    --agree-tos \
    --register-unsafely-without-email


# Convert the generated certificate to a .pfx
CERT_DIR="${ledir}/live/${fqdn}"
CERT_PASSWORD=$(openssl rand -base64 30)
openssl pkcs12 -export \
    -inkey "${CERT_DIR}/privkey.pem" \
    -in "${CERT_DIR}/fullchain.pem" \
    -out "${CERT_DIR}/aci.pfx" \
    -passout "pass:${CERT_PASSWORD}"

if [[ -n ${keyvault_name} ]]; then
    sid=$(az keyvault certificate import \
        -o json \
        --vault-name "${keyvault_name}" \
        --name "${cert_name}" \
        --file "${CERT_DIR}/aci.pfx" \
        --password "${CERT_PASSWORD}" \
        | jq -r '.sid')

    # Save the certificate password to KV
    az keyvault secret set --name "${cert_name}"-password \
      --vault-name "${keyvault_name}" \
      --value "${CERT_PASSWORD}"

    az network application-gateway ssl-cert update \
        --resource-group "${resource_group_name}" \
        --gateway-name "${application_gateway_name}" \
        --name 'cert-primary' \
        --key-vault-secret-id "${sid}"
else
    az network application-gateway ssl-cert update \
        --resource-group "${resource_group_name}" \
        --gateway-name "${application_gateway_name}" \
        --name "${cert_name}" \
        --cert-file "${CERT_DIR}/aci.pfx" \
        --cert-password "${CERT_PASSWORD}"
fi
