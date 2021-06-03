#!/bin/bash
set -e

az acr login --name $TF_VAR_acr_name
porter publish --dir ./workspaces/vanilla/ --file ./workspaces/vanilla/porter.yaml --registry "$TF_VAR_acr_name.azurecr.io/microsoft/azuretre/workspaces" --debug
