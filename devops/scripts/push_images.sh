#!/bin/bash
set -e

ACR_NAME="${TF_VAR_resource_name_prefix}acr"
az acr login --name $ACR_NAME

if [ "$1" == "api" ]; then
    docker push "$ACR_NAME.azurecr.io/microsoft/azuretre/management-api":$TF_VAR_image_tag
elif [ "$1" == "cnab" ]; then
    docker push "$ACR_NAME.azurecr.io/microsoft/azuretre/cnab-aci":$TF_VAR_image_tag
fi
