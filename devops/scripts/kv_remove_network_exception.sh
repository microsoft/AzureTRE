#!/bin/bash

function main() {

    set -o errexit
    set -o pipefail

    # attempt to determine our tre id
    #
    local TRE_ID_LOCAL="${TRE_ID:-}"

    if [[ -z "$TRE_ID_LOCAL" ]]; then
      if [[ "${core_tre_rg:-}" == rg-* ]]; then  # TRE_ID may not be available when called from destroy_env_no_terraform.sh
        TRE_ID_LOCAL="${core_tre_rg#rg-}"
      fi
    fi

    if [[ -z "$TRE_ID_LOCAL" ]]; then
      echo -e "Could not remove keyvault deployment network exception: TRE_ID is not set\nExiting...\n"
      exit 1
    fi

    # set up variables
    #
    local RG_NAME="rg-${TRE_ID_LOCAL}"
    local KV_NAME="kv-${TRE_ID_LOCAL}"
    local MY_IP="${PUBLIC_DEPLOYMENT_IP_ADDRESS:-}"

    if [[ -z "$MY_IP" ]]; then
      MY_IP=$(curl -s "ipecho.net/plain"; echo)
    fi


    # remove keyvault network exception
    #
    echo -e "\nRemoving deployment network exception to key vault $KV_NAME..."

    if [[ -z "$(az group list --query "[?name=='$RG_NAME']" --output tsv)" ]]; then
        echo -e " Core resource group $RG_NAME not found\n"
        return 0
    fi

    if [[ -z "$(az keyvault list --resource-group "$RG_NAME" --query "[?name=='$KV_NAME'].id" --output tsv)" ]]; then
        echo -e " Core key vault $KV_NAME not found\n"
        return 0
    fi

    az keyvault network-rule remove --name "$KV_NAME" --ip-address "$MY_IP" --output none
    echo -e " Deployment network exception removed\n"

}

main "$@"
