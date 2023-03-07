#!/bin/bash
set -e

acr_domain=$(az cloud show --query suffixes.acrLoginServerEndpoint --output tsv)

porter install tre-service-azureml --reference "${MGMT_ACR_NAME}${acr_domain}/tre-service-azureml:v0.1.9" \
    --cred ./arm_auth_local_debugging.json \
    --parameter-set ./parameters_service_azureml.json
