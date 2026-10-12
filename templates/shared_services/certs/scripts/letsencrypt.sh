#!/bin/bash
set -e
set -o pipefail
umask 077

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")

while [ "$1" != "" ]; do
    case $1 in
    --storage_account_name)
        shift
        storage_account_name=$1
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
    --password_name)
        shift
        password_name=$1
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

work_dir=$(mktemp -d)
trap 'rm -rf "$work_dir"' EXIT
cache_args=(--cert-name "$cert_name" --vault "$keyvault_name" --fqdn "$fqdn" --directory "$work_dir")

if python3 "${script_dir}/certificate_cache.py" restore "${cache_args[@]}"; then
    echo "Using the retained certificate without an ACME request"
else
    cache_status=$?
    if [[ "$cache_status" -ne 3 ]]; then
        exit "$cache_status"
    fi
    echo "Checking for index.html file in storage account"

    # Create the default index.html page
    cat << EOF > "${work_dir}/index.html"
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
        echo "No existing file found. Uploading index.html file"

        # shellcheck disable=SC2016
        az storage blob upload \
            --account-name "${storage_account_name}" \
            --auth-mode login \
            --container-name '$web' \
            --file "${work_dir}/index.html" \
            --name index.html \
            --no-progress \
            --only-show-errors

        # Wait a bit for the App Gateway health probe to notice
        echo "Waiting 30s for app gateway health probe"
        sleep 30s
    else
        echo "index.html already present"
    fi

    ledir="${work_dir}/letsencrypt"
    mkdir -p "${ledir}/logs"

    # Initiate the ACME challenge
    echo "Initiating ACME challenge"
    export STORAGE_ACCOUNT_NAME="${storage_account_name}"
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

    cp "${ledir}/live/${fqdn}/privkey.pem" "${work_dir}/privkey.pem"
    cp "${ledir}/live/${fqdn}/fullchain.pem" "${work_dir}/fullchain.pem"
    # Persist issuance before updating the service alias. A later failure can reuse it.
    python3 "${script_dir}/certificate_cache.py" store "${cache_args[@]}"
fi

# Convert the generated certificate to a .pfx
echo "Got cert. Converting to PFX"
CERT_DIR="${work_dir}"
CERT_PASSWORD=$(openssl rand -base64 30)
printf %s "$CERT_PASSWORD" > "${CERT_DIR}/password"
openssl pkcs12 -export \
    -inkey "${CERT_DIR}/privkey.pem" \
    -in "${CERT_DIR}/fullchain.pem" \
    -out "${CERT_DIR}/aci.pfx" \
    -passout "file:${CERT_DIR}/password"

# Save cert and password to KeyVault
echo "Importing cert to KeyVault ${keyvault_name}"
sid=$(az keyvault certificate import \
    -o json \
    --vault-name "${keyvault_name}" \
    --name "${cert_name}" \
    --file "${CERT_DIR}/aci.pfx" \
    --password "${CERT_PASSWORD}" \
    | jq -r '.sid')

echo "Saving certificate password to KV with key ${password_name}"
az keyvault secret set --name "$password_name" \
  --vault-name "${keyvault_name}" \
  --file "${CERT_DIR}/password" \
  --output none --only-show-errors

echo "Updating SSL cert in app gateway"
az network application-gateway ssl-cert update \
    --resource-group "${resource_group_name}" \
    --gateway-name "${application_gateway_name}" \
    --name 'cert-primary' \
    --key-vault-secret-id "${sid}"
