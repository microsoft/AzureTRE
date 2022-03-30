#!/bin/bash
set -e

# This script polls looking for an app registration with the given ID.
# If after the number of retries no app registration is found, the function exits.
servicePrincipalId=$1
retries=10
counter=0
output=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/servicePrincipals/${servicePrincipalId}" 2>/dev/null || true)

while [[ -z $output && $counter -lt $retries ]]; do
    counter=$((counter+1))
    echo "Waiting for service principal with ID ${servicePrincipalId} to show up (${counter}/${retries})..."
    sleep 5
    output=$(az rest --method GET --uri "https://graph.microsoft.com/v1.0/servicePrincipals/${servicePrincipalId}" 2>/dev/null || true)
done

if [[ -z $output ]]; then
    echo "Failed"
    exit 1
fi

echo "Service principal with ID ${servicePrincipalId} found"
