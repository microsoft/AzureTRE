#!/bin/bash

# Check the service principal is set for deploying Shared Services.
if [[ -z "${ARM_TENANT_ID}" || -z "${ARM_CLIENT_ID}" || -z "${ARM_CLIENT_SECRET}" ]]; then
  echo "Currently, you need to create a Service Principal to deploy Shared Services (Firewall, Gitea and Nexus)."
  echo "Creating a service principal.."
  SP_NAME="SharedServiceDeployer"
  # Create a Service Principal and query it's ID
  CLIENT_ID=$(az ad sp create-for-rbac --name ${SP_NAME} --role Contributor --query 'appId' --output tsv)
  CLIENT_SECRET=$(az ad sp credential reset --name ${CLIENT_ID} --query 'password' --output tsv)

  echo "Please set the following values in \
    templates/shared_services/firewall/.env,
    templates/shared_services/gitea/.env,
    templates/shared_services/sonatype-nexus/.env"
    cat << ENV_VARS
Variables:

ARM_TENANT_ID=$(az account show --output json | jq -r '.tenantId')
ARM_CLIENT_ID=${CLIENT_ID}
ARM_CLIENT_SECRET=${CLIENT_SECRET}

ENV_VARS

  # Prevent consequent scripts from running
  exit 1
  fi
