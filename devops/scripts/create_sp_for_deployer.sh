#!/bin/bash
set -e

# This script creates a service principal for deploying resources (workspaces and workspace services).
# Provided to the deployment processor via Terraform.
#
# If a service principal already exists, the client secret (app password) gets changed but the ID will remain the same.
#
# Required environment variables set before running this script are:
#
#   - $SUB_ID - Azure subscription ID
#   - $DEPLOYMENT_PROCESSOR_SERVICE_PRINCIPAL_NAME - The name for the service principal
#
# The client (app) ID and client secret (app password) are inserted in the following environment variables:
#
#   - TF_VAR_deployment_processor_azure_client_id
#   - TF_VAR_deployment_processor_azure_client_secret
#
# Make sure to run the script in the current process (not in a new process/environment) so that the environment variables
# get carried over. Use the dot or source syntax to do this:
#
#     $ . ./create_sp_for_deployer.sh
#
#       - OR -
#
#     $ source ./create_sp_for_deployer.sh
#

echo -e "\n\e[34m»»» 🤖 \e[96mCreating service principal\e[0m..."
az account set --subscription $SUB_ID

# Scope defaults to the root of the current subscription. e.g., /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333
az_output=`az ad sp create-for-rbac --name $DEPLOYMENT_PROCESSOR_SERVICE_PRINCIPAL_NAME --role Contributor --sdk-auth`

client_id=`echo "$az_output" | jq -r '.clientId'`
client_secret=`echo "$az_output" | jq -r '.clientSecret'`

export TF_VAR_deployment_processor_azure_client_id=$client_id
export TF_VAR_deployment_processor_azure_client_secret=$client_secret
