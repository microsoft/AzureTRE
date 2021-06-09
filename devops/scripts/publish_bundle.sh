#!/bin/bash
set -e

az acr login --name $TF_VAR_acr_name
porter publish --registry "$TF_VAR_acr_name.azurecr.io" --debug
