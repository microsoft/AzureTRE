#!/bin/bash

function main() {

    set -o errexit
    set -o pipefail

    # parse params/set up inputs
    #
    if [[ -z "$TRE_ID" ]]; then
      echo -e "Could not add keyvault deployment network exception: TRE_ID is not set\nExiting...\n"
      exit 1
    fi

    local RG_NAME="rg-${TRE_ID}"
    local KV_NAME="kv-${TRE_ID}"
    local MY_IP="${PUBLIC_DEPLOYMENT_IP_ADDRESS:-}"

    if [[ -z "$MY_IP" ]]; then
      MY_IP=$(curl -s "ipecho.net/plain"; echo)
    fi


    # add keyvault network exception
    #
    echo -e "\nAdding deployment network exception to key vault $KV_NAME..."

    if [[ -z "$(az group list --query "[?name=='$RG_NAME']" --output tsv)" ]]; then
        echo -e " Core resource group $RG_NAME not found\n"
        return 0
    fi

    if [[ -z "$(az keyvault list --resource-group "$RG_NAME" --query "[?name=='$KV_NAME'].id" --output tsv)" ]]; then
        echo -e " Core key vault $KV_NAME not found\n"
        return 0
    fi

    az keyvault network-rule add --resource-group "$RG_NAME" --name "$KV_NAME" --ip-address "$MY_IP" --output none

    local ATTEMPT=1
    local MAX_ATTEMPTS=10

    while true; do

      if KV_OUTPUT=$(az keyvault secret list --vault-name "$KV_NAME" --query '[].name' --output tsv 2>&1); then
        echo -e " Keyvault $KV_NAME is now accessible\n"
        break
      fi

      if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo -e "Could not add deployment network exception for $KV_NAME"
        echo -e "Unable to access keyvault $KV_NAME after $ATTEMPT/$MAX_ATTEMPTS.\n"
        echo -e "$KV_OUTPUT\n"

        exit 1
      fi

      echo " Unable to access keyvault $KV_NAME after $ATTEMPT/$MAX_ATTEMPTS. Waiting for network rules to take effect."
      sleep 5
      ((ATTEMPT++))

    done

}

main "$@"
