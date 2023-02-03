#!/bin/bash
set -e


porter install tre-service-azureml --reference "${MGMT_ACR_NAME}.azurecr.io/tre-service-azureml:v0.1.9" \
    --cred ./arm_auth_local_debugging.json \
    --parameter-set ./parameters_service_azureml.json
