#!/bin/bash
set -e

function usage() {
    cat <<USAGE

    Usage: $0  [-t --tre-id]

    Options:
        -t, --tre-id               ID of the TRE
USAGE
    exit 1
}

# if no arguments are provided, return usage function
if [ $# -eq 0 ]; then
    usage # run usage function
fi

while [ "$1" != "" ]; do
    case $1 in
    -t | --tre-id)
        shift
        tre_id=$1
        ;;
    esac
    if [[ -z "$2" ]]; then
      # if no more args then stop processing
      break
    fi
    shift # remove the current value for `$1` and use the next
done

export NEXUS_URL="https://nexus-${tre_id}.azurewebsites.net"
export NEXUS_ADMIN_PASSWORD_NAME="nexus-${tre_id,,}-admin-password"
export KEYVAULT_NAME="kv-${tre_id}"
export STORAGE_ACCOUNT_NAME="stg${tre_id//-/}"

export NEXUS_PASS=$(az keyvault secret show --name ${NEXUS_ADMIN_PASSWORD_NAME} --vault-name ${KEYVAULT_NAME} -o json | jq -r '.value')

if [ -z "$NEXUS_PASS" ]; then
    # The pass couldn't be found in Key Vault, fetching from nexus_data
    while [ $(az storage file exists -p admin.password -s nexus-data --account-name ${STORAGE_ACCOUNT_NAME,,} -o json | jq '.exists') == false ]; do
        echo "Waiting for admin pass..."
        sleep 10
    done

    # The initial password file exists, let's get it
    az storage file download -p admin.password -s nexus-data --account-name ${STORAGE_ACCOUNT_NAME,,}
    export NEXUS_PASS=`cat admin.password`

    #we have the initial password; let's try to connect to Nexus and reset the password
    export NEW_PASSWORD=$(date +%s | sha256sum | base64 | head -c 32 ; echo)

    curl -ifu admin:$NEXUS_PASS \
         -XPUT -H 'Content-Type: text/plain' \
         --data "${NEW_PASSWORD}" \
        $NEXUS_URL/service/rest/v1/security/users/admin/change-password

    #Let's store the new pass into Key Vault
    az keyvault secret set --name ${NEXUS_ADMIN_PASSWORD_NAME} --vault-name ${KEYVAULT_NAME} --value $NEW_PASSWORD
    export NEXUS_PASS=$NEW_PASSWORD
fi

#Check if the repo already exists
 export STATUS_CODE=$(curl -iu admin:$NEXUS_PASS -X "GET" "${NEXUS_URL}/service/rest/v1/repositories/apt/proxy/ubuntu-proxy-repo" -H "accept: application/json" -k -s -w "%{http_code}" -o /dev/null)

 if [[ ${STATUS_CODE} == 404 ]]
  then
     # Let's create ubuntu library proxy
     curl -iu admin:$NEXUS_PASS -XPOST \
     $NEXUS_URL/service/rest/v1/repositories/apt/proxy \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '@./scripts/ubuntu_proxy_conf.json'
 fi

 #Check if the repo already exists
 export STATUS_CODE=$(curl -iu admin:$NEXUS_PASS -X "GET" "${NEXUS_URL}/service/rest/v1/repositories/apt/proxy/ubuntu-security-proxy-repo" -H "accept: application/json" -k -s -w "%{http_code}" -o /dev/null)

 if [[ ${STATUS_CODE} == 404 ]]
  then
     # Let's create ubuntu security library proxy
     curl -iu admin:$NEXUS_PASS -XPOST \
     $NEXUS_URL/service/rest/v1/repositories/apt/proxy \
     -H 'accept: application/json' \
     -H 'Content-Type: application/json' \
     -d '@./scripts/ubuntu_security_proxy_conf.json'
 fi

#Check if the repo already exists
export STATUS_CODE=$(curl -iu admin:$NEXUS_PASS -X "GET" "${NEXUS_URL}/service/rest/v1/repositories/apt/proxy/pypi-proxy-repo" -H "accept: application/json" -k -s -w "%{http_code}" -o /dev/null)

if [[ ${STATUS_CODE} == 404 ]]
 then
    # Let's create pypi proxy
    curl -iu admin:$NEXUS_PASS -XPOST \
    $NEXUS_URL/service/rest/v1/repositories/apt/proxy \
    -H 'accept: application/json' \
    -H 'Content-Type: application/json' \
    -d '@./scripts/pypi_proxy_conf.json'
fi
