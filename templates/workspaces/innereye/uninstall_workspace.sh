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

az network firewall network-rule collection delete \
  --collection-name "nrc-${TRE_ID}-ws-${SHORT_ID}-svc-${SHORT_ID}" \
  --firewall-name "fw-${TRE_ID}" \
  --resource-group "rg-${TRE_ID}"

az network firewall application-rule collection delete \
  --collection-name "arc-${TRE_ID}-ws-${SHORT_ID}-svc-${SHORT_ID}" \
  --firewall-name "fw-${TRE_ID}" \
  --resource-group "rg-${TRE_ID}"

az network firewall application-rule collection delete \
  --collection-name "arc-${TRE_ID}-ws-${SHORT_ID}-svc-${SHORT_ID}-aml" \
  --firewall-name "fw-${TRE_ID}" \
  --resource-group "rg-${TRE_ID}"
