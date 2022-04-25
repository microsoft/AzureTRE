#!/bin/bash
set -e

porter install tre-service-innereye --reference "${MGMT_ACR_NAME}.azurecr.io/tre-service-innereye:v0.1.5" \
    --cred ./arm_auth_local_debugging.json \
    --parameter-set ./parameters_service_innereye.json \
    --allow-docker-host-access \
    --debug
