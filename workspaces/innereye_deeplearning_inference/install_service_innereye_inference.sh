#!/bin/bash
set -e

export AZUREML_WORKSPACE_NAME=$(porter installations output show azureml_workspace_name -i tre-service-azureml | tr -d '"')
export AZUREML_COMPUTE_CLUSTER_NAME=$(porter installations output show azureml_compute_cluster_name -i tre-service-innereye-deeplearning | tr -d '"')

porter install --reference "${ACR_NAME}.azurecr.io/tre-service-innereye-inference:v0.1.0" \
    --cred ./azure.json \
    --parameter-set ./parameters_service_innereye-inference.json \
    --debug