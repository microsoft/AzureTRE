#!/bin/bash

# This script creates a new service principal with a "Contributor" role and the scope for the root of the given subscription.
# The client (app) ID and the client secret (app password) are inserted into environment variables:
# - NEW_AZURE_CLIENT_ID
# - NEW_AZURE_CLIENT_SECRET
#
# Make sure to run the script in the current process (not in a new process/environment) so that the environment variables
# get carried over. Use the dot or source syntax to do this:
#
#     $ . ./create_service_principal.sh sp-my-principal-name 0b1f6471-1bf0-4dda-aec3-111122223333
#
#       - OR -
#
#     $ source ./create_service_principal.sh sp-my-principal-name 0b1f6471-1bf0-4dda-aec3-111122223333
#

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: . $0 <service principal name> <subscription ID>"
    exit 1
fi

service_principal_name=$1
subscription_id=$2

az account set --subscription $subscription_id

# Scope defaults to the root of the current subscription. e.g., /subscriptions/0b1f6471-1bf0-4dda-aec3-111122223333
az_output=`az ad sp create-for-rbac --name $service_principal_name --role Contributor --sdk-auth`

client_id=`echo "$az_output" | jq -r '.clientId'`
client_secret=`echo "$az_output" | jq -r '.clientSecret'`

export NEW_AZURE_CLIENT_ID=$client_id
export NEW_AZURE_CLIENT_SECRET=$client_secret
