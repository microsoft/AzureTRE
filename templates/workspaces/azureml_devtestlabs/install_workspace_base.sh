#!/bin/bash
set -e

porter install tre-workspace-base --reference "${ACR_NAME}.azurecr.io/tre-workspace-base:v0.1.0" \
    --cred ./azure.json \
    --parameter-set ./parameters_workspace_base.json \
    --debug