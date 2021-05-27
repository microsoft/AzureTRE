#!/bin/bash
set -e

ACR_NAME="${TF_VAR_resource_name_prefix}acr"
az acr login --name $ACR_NAME
porter publish --dir ./workspaces/vanilla/ --file ./workspaces/vanilla/porter.yaml --registry "$ACR_NAME.azurecr.io/microsoft/azuretre/workspaces" --debug
