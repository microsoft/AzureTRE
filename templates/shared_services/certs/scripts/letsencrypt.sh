#!/bin/bash
set -e
set -o pipefail
umask 077

script_dir=$(realpath "$(dirname "${BASH_SOURCE[0]}")")
# Installation retries must restart the gateway stopped by the previous attempt.
start_gateway=true

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
    --start_gateway)
        shift
        start_gateway=$1
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

work_dir=""
cleanup() {
    local script_exit=$?
    trap - EXIT
    if [[ -n "$work_dir" ]] && ! rm -rf "$work_dir"; then
        echo "Failed to remove temporary certificate files" >&2
        if [[ "$script_exit" -eq 0 ]]; then script_exit=1; fi
    fi
    if ! az network application-gateway stop \
        --resource-group "$resource_group_name" \
        --name "$application_gateway_name" \
        --output none --only-show-errors; then
        echo "Failed to stop the certificate application gateway. Check its state before retrying." >&2
        if [[ "$script_exit" -eq 0 ]]; then script_exit=1; fi
    fi
    exit "$script_exit"
}
trap cleanup EXIT

case "$start_gateway" in
    true)
        az network application-gateway start \
            --resource-group "$resource_group_name" \
            --name "$application_gateway_name" \
            --output none --only-show-errors
        ;;
    false) ;;
    *) echo "start_gateway must be true or false" >&2; exit 2 ;;
esac

work_dir=$(mktemp -d)
reuse_certificate=false
reuse_current=false
reuse_args=(--cert-name "$cert_name" --vault "$keyvault_name" --fqdn "$fqdn" --directory "$work_dir")

if python3 "${script_dir}/certificate_reuse.py" restore "${reuse_args[@]}"; then
    reuse_certificate=true
    reuse_current=$(jq -er '
        select((.is_current | type) == "boolean")
        | select(.content_type == "application/x-pkcs12" or .content_type == "application/x-pem-file")
        | (.is_current and (.content_type == "application/x-pkcs12")) | tostring
    ' "${work_dir}/reuse.json")
    if [[ "$reuse_current" == true ]]; then
        sid=$(jq -er '.secret_id | select(type == "string" and length > 0)' "${work_dir}/reuse.json")
    fi
else
    reuse_status=$?
    if [[ "$reuse_status" -ne 3 ]]; then
        exit "$reuse_status"
    fi
fi

if [[ "$reuse_certificate" == false ]]; then
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
    python3 "${script_dir}/certificate_reuse.py" validate \
        --fqdn "$fqdn" --directory "$work_dir"
fi

if [[ "$reuse_current" == false ]]; then
    # Import new certificates, older recovered versions or PEM material converted to PFX.
    echo "Got cert. Converting to PFX"
    CERT_DIR="${work_dir}"
    CERT_PASSWORD=$(openssl rand -base64 30)
    printf %s "$CERT_PASSWORD" > "${CERT_DIR}/password"
    openssl pkcs12 -export \
        -inkey "${CERT_DIR}/privkey.pem" \
        -in "${CERT_DIR}/fullchain.pem" \
        -out "${CERT_DIR}/aci.pfx" \
        -passout "file:${CERT_DIR}/password"

    # Store the issued material before updating the password or gateway.
    # A later failure can reuse this certificate on retry.
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
fi

echo "Updating SSL cert in app gateway"
az network application-gateway ssl-cert update \
    --resource-group "${resource_group_name}" \
    --gateway-name "${application_gateway_name}" \
    --name 'cert-primary' \
    --key-vault-secret-id "${sid}"
