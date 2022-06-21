#!/bin/bash
set -e

porter install tre-workspace-base --reference "${MGMT_ACR_NAME}.azurecr.io/tre-workspace-base:v0.1.5" \
    --cred ./arm_auth_local_debugging.json \
    --parameter-set ./parameters_workspace_base.json \
    --debug
