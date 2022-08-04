#!/bin/bash

# This script is designed to be `source`d to create reusable helper functions

# Notes: Before Az CLI 2.37 this would return a json document with .objectId; that is now .id

# This script polls looking for an app registration with the given ID.
# If after the number of retries no app registration is found, the function exits.
function wait_for_new_app_registration()
{
  local clientId=$1
  local retries=10
  local counter=0

  objectId=$(az ad app list --filter "appId eq '${clientId}'" --query '[0].id' --output tsv --only-show-errors)

  while [[ -z $objectId && $counter -lt $retries ]]; do
      counter=$((counter+1))
      echo "Waiting for app registration with ID ${clientId} to show up (${counter}/${retries})..."
      sleep 5
      objectId=$(az ad app list --filter "appId eq '${clientId}'" --query '[0].id' --output tsv --only-show-errors)
  done

  if [[ -z $objectId ]]; then
      echo "Failed"
      exit 1
  fi

  echo "App registration \"${clientId}\" found."
}
