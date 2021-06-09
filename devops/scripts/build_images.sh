#!/bin/bash
set -e

if [ "$1" == "api" ]; then
    docker build -t "${TF_VAR_acr_name}.azurecr.io/microsoft/azuretre/management-api:${TF_VAR_image_tag}" ./management_api_app/
elif [ "$1" == "cnab" ]; then
    docker build -t "${TF_VAR_acr_name}.azurecr.io/microsoft/azuretre/cnab-aci:${TF_VAR_image_tag}" -t cnab-aci ./CNAB_container
fi