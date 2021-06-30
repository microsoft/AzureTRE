#!/bin/bash
set -e

porter install tre-service-innereye-devtestlabs --reference "${ACR_NAME}.azurecr.io/tre-service-innereye-devtestlabs:v0.1.0" \
    --cred ./azure.json \
    --parameter-set ./parameters_service_innereye-devtestlabs.json \
    --debug