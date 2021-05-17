#!/bin/bash
# This provisions terraform state storage account and container and generates backend file for terraform

location="westeurope"
resource_group_name="rg-terraform-state"
storage_account_name="tfstate$(uuidgen | cut -c1-8)"
container_name="tfstate"

az group create -n $resource_group_name -l $location
az storage account create -n $storage_account_name -l $location -g $resource_group_name
az storage container create -n $container_name --account-name $storage_account_name --auth-mode login

backend_tfvars="../templates/backend.tfvars"
cat <<EOF > $backend_tfvars 
resource_group_name  = "$resource_group_name"
storage_account_name = "$storage_account_name"
container_name = "$container_name"
EOF

