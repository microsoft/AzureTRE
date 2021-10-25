#!/bin/bash
set -e

TRE_ID=$1
ID=$2
SHORT_ID=${ID: -4}

az group delete \
  --name "rg-${TRE_ID}-ws-${SHORT_ID}" --yes

az network vnet peering delete \
  --resource-group "rg-${TRE_ID}" \
  --name "core-ws-peer-${TRE_ID}-ws-${SHORT_ID}" \
  --vnet-name "vnet-${TRE_ID}"
