#!/bin/bash

TRE_DEPLOYMENT_NETWORK_EXCEPTION_TAG="tre_deployment_network_exception"

function main() {

    set -o errexit
    set -o pipefail


    # parse params/set up inputs
    #
    if [[ -z "$TRE_ID" ]]; then
      echo -e "Could not close deployment network exceptions: TRE_ID is not set\nExiting...\n"
      exit 1
    fi

    local MY_IP="${PUBLIC_DEPLOYMENT_IP_ADDRESS:-}"

    if [[ -z "$MY_IP" ]]; then
      MY_IP=$(curl -s "ipecho.net/plain"; echo)
    fi

    local TRE_CORE_RG="rg-${TRE_ID}"


    # find resources that require network exceptions
    #
    echo -e "\nQuerying resources that require network exceptions removing for deployment..."

    if [[ -z "$(az group list --query "[?name=='$TRE_CORE_RG']" --output tsv)" ]]; then
        echo -e " Core resource group $TRE_CORE_RG not found\n"
        return 0
    fi

    local AZ_IDS
    AZ_IDS=$(az resource list --resource-group "$TRE_CORE_RG" --query "[?tags.${TRE_DEPLOYMENT_NETWORK_EXCEPTION_TAG}=='true'].id" --output tsv)

    if [ -z "$AZ_IDS" ]; then
      echo -e " No resources found\n"
      return 0
    fi


    # remove network exceptions
    #
    local AZ_ID
    for AZ_ID in $AZ_IDS; do

      local RESOURCE_TYPE
      RESOURCE_TYPE=$(az resource show --ids "${AZ_ID}" --query 'type' --output tsv)

      if [ "$RESOURCE_TYPE" == "Microsoft.KeyVault/vaults" ]; then
        remove_keyvault_network_exception "$AZ_ID" "$MY_IP"
      fi

    done

    echo ""

}

function remove_keyvault_network_exception() {
  local AZ_ID="$1"
  local MY_IP="$2"

  local KV_NAME
  KV_NAME=$(basename "$AZ_ID")

  echo " Removing keyvault deployment network exception for $KV_NAME"

  az keyvault network-rule remove --name "$KV_NAME" --ip-address "$MY_IP" --output none
}

main "$@"
