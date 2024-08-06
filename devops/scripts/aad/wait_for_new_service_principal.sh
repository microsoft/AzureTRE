#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

# This script polls looking for an app registration with the given ID.
# If after the number of retries no app registration is found, the function exits.
function wait_for_new_service_principal()
{
  servicePrincipalId=$1
  retries=10
  counter=0
  local msGraphUri=""
  msGraphUri="$(az cloud show --query endpoints.microsoftGraphResourceId --output tsv)/v1.0"

  output=$(az rest --method GET --uri "${msGraphUri}/servicePrincipals/${servicePrincipalId}" 2>/dev/null || true)

  while [[ -z $output && $counter -lt $retries ]]; do
      counter=$((counter+1))
      echo "Waiting for service principal with ID ${servicePrincipalId} to show up (${counter}/${retries})..."
      sleep 5
      output=$(az rest --method GET --uri "${msGraphUri}/servicePrincipals/${servicePrincipalId}" 2>/dev/null || true)
  done

  if [[ -z $output ]]; then
      echo "Failed"
      exit 1
  fi

  echo "Service principal with ID ${servicePrincipalId} found"
}
