#!/bin/bash
set -e

az acr login --name $TF_VAR_acr_name

if [ "$1" == "api" ]; then
    docker push "$TF_VAR_acr_name.azurecr.io/microsoft/azuretre/management-api":$TF_VAR_image_tag
elif [ "$1" == "cnab" ]; then
    docker push "$TF_VAR_acr_name.azurecr.io/microsoft/azuretre/cnab-aci":$TF_VAR_image_tag
fi
