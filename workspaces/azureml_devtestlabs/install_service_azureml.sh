#!/bin/bash
set -e

export AZUREML_WORKSPACE_NAME=$(porter installations output show azureml_workspace_name -i service-azureml_devtestlabs | tr -d '"')
export AZUREML_ACR_ID=$(porter installations output show azureml_acr_id -i service-azureml_devtestlabs | tr -d '"')

porter install tre-service-azureml --reference "${ACR_NAME}.azurecr.io/tre-service-azureml:v0.1.2" \
    --cred ./azure.json \
    --parameter-set ./parameters_service_azureml.json \
    --debug