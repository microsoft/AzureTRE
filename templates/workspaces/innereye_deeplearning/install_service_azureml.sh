#!/bin/bash
set -e

porter install tre-service-azureml --reference "${ACR_NAME}.azurecr.io/tre-service-azureml:v0.1.5" \
    --cred ./azure.json \
    --parameter-set ./parameters_service_azureml.json \
    --debug