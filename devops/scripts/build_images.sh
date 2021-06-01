#!/bin/bash
set -e

if [ "$1" == "api" ]; then
    docker build -t "${TF_VAR_resource_name_prefix}acr.azurecr.io/microsoft/azuretre/management-api:${TF_VAR_image_tag}" ./management_api_app/
elif [ "$1" == "cnab" ]; then
    docker build -t "${TF_VAR_resource_name_prefix}acr.azurecr.io/microsoft/azuretre/cnab-aci:${TF_VAR_image_tag}" ./CNAB_container
fi