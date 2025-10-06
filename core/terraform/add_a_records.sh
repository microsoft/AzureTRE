#!/bin/bash

# Login with ARM App Registration
az login --service-principal --allow-no-subscriptions --tenant "${TENANT_ID}" --username "${ARM_CLIENT_ID}" --password "${ARM_CLIENT_SECRET}"

# Find IP of SQL Server VM
PRIVATE_IP_SQL=$(az vm list-ip-addresses -g "$DATA_SHARED_RG" -n "$SQL_VM_NAME" --query "[0].virtualMachine.network.privateIpAddresses[0]" -o tsv)

# Add DNS Record for SQL Server VM
az network private-dns record-set a add-record --ipv4-address "$PRIVATE_IP_SQL" --record-set-name "$SQL_RECORD_SET_NAME" --resource-group "$CORE_RESOURCE_GROUP" --zone-name "$SQL_ZONE_NAME"

# Find IP of Synapse SQL Private Endpoint - privateIPAddress needs to be with a lowercase IP because of the newer version of az-cli
NIC_ID_PE_SYNAPSE_SQL=$(az network private-endpoint show --name "$PE_SYNAPSE_SQL" --resource-group "$DATA_SHARED_RG" --query "networkInterfaces[0].id" -o tsv)
PRIVATE_IP_SYNAPSE_SQL=$(az network nic show --ids "$NIC_ID_PE_SYNAPSE_SQL" --query "ipConfigurations[0].privateIpAddress" -o tsv)

# Add DNS Record for Synapse SQL Private Endpoint
az network private-dns record-set a add-record --ipv4-address "$PRIVATE_IP_SYNAPSE_SQL" --record-set-name "$SYNAPSE_SQL_RECORD_SET_NAME" --resource-group "$CORE_RESOURCE_GROUP" --zone-name "$SYNAPSE_ZONE_NAME"

# Find IP of Synapse SQL Ondemand Private Endpoint - privateIPAddress needs to be with a lowercase IP because of the newer version of az-cli
NIC_ID_PE_SYNAPSE_SQL_ONDEMAND=$(az network private-endpoint show --name "$PE_SYNAPSE_SQL_ONDEMAND" --resource-group "$DATA_SHARED_RG" --query "networkInterfaces[0].id" -o tsv)
PRIVATE_IP_SYNAPSE_SQL_ONDEMAND=$(az network nic show --ids "$NIC_ID_PE_SYNAPSE_SQL_ONDEMAND" --query "ipConfigurations[0].privateIpAddress" -o tsv)

# Add DNS Record for Synapse Ondemand SQL Private Endpoint
az network private-dns record-set a add-record --ipv4-address "$PRIVATE_IP_SYNAPSE_SQL_ONDEMAND" --record-set-name "$SYNAPSE_SQL_ONDEMAND_RECORD_SET_NAME" --resource-group "$CORE_RESOURCE_GROUP" --zone-name "$SYNAPSE_ZONE_NAME"
