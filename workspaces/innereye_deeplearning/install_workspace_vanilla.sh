#!/bin/bash
set -e

porter install tre-workspace-vanilla --reference "${ACR_NAME}.azurecr.io/tre-workspace-vanilla:v0.1.0" \
    --cred ./azure.json \
    --parameter-set ./parameters_workspace_vanilla.json \
    --debug