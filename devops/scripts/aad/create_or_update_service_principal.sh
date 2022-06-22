#!/bin/bash
set -e

# This script polls looking for an app registration with the given ID.
# If after the number of retries no app registration is found, the function exits.
function wait_for_new_service_principal()
{
  servicePrincipalId=$1
  retries=10
  counter=0
  local msGraphUri="https://graph.microsoft.com/v1.0"

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

  #echo "Service principal with ID ${servicePrincipalId} found"
}

# This script creates a new Service Principal or offers to update the password if it already exists.
function create_or_update_service_principal()
{
  applicationId=$1
  appName=$2

  # See if a service principal already exists
  spId=$(az ad sp list --filter "appId eq '${applicationId}'" --query '[0].objectId' --output tsv --only-show-errors)

  resetPassword=0

  # If not, create a new service principal
  if [[ -z "$spId" ]]; then
      spId=$(az ad sp create --id "${applicationId}" --query 'objectId' --output tsv --only-show-errors)
      wait_for_new_service_principal "${spId}"
      az ad app owner add --id "${applicationId}" --owner-object-id "${spId}" --only-show-errors
      resetPassword=1
  else
      read -p "Service principal for \"${appName}\" already exists. Do you wish to reset the password (y/N)? " -n 1 -r

      if [[ $REPLY =~ ^[Yy]$ ]]; then
          resetPassword=1
      fi
  fi

  spPassword=""

  if [[ "$resetPassword" == 1 ]]; then
      spPassword=$(az ad sp credential reset --name "${applicationId}" --query 'password' --output tsv --only-show-errors)
  fi

  # This tag ensures the app is listed in "Enterprise applications"
  az ad sp update --id "$spId" --set tags="['WindowsAzureActiveDirectoryIntegratedApp']" --only-show-errors

  echo "${spPassword}"
}
