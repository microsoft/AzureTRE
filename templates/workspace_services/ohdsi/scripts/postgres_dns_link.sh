#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

link_name="core"

result=$(az network private-dns link vnet list --resource-group "${RESOURCE_GROUP}" -z "${DNS_ZONE_NAME}" --query "[?name=='${link_name}'] | length(@)")

if [[  "${result}" == 0 ]];
then
  az network private-dns link vnet create \
    --name ${link_name} --resource-group "${RESOURCE_GROUP}" --virtual-network "${VNET}" --zone-name "${DNS_ZONE_NAME}" \
    --registration-enabled false
else
  echo "Zone already linked."
fi
