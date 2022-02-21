#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

export TF_VAR_docker_registry_server="$TF_VAR_acr_name.azurecr.io"
export TF_VAR_docker_registry_username=$TF_VAR_acr_name
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_acr_name} --query passwords[0].value -o tsv | sed 's/"//g')

PLAN_FILE="tfplan$$"
LOG_FILE="tmp$$.log"

../../../devops/scripts/terraform_wrapper.sh \
  -g $TF_VAR_mgmt_resource_group_name \
  -s $TF_VAR_mgmt_storage_account_name \
  -n $TF_VAR_terraform_state_container_name \
  -k ${TRE_ID} \
  -l ${LOG_FILE} \
  -c "terraform plan -out ${PLAN_FILE} && terraform state list"
 # terraform apply -input=false -auto-approve ${PLAN_FILE} && \  # TODO(tanya): don't forget to remove!!!
 #  terraform output -json > ../tre_output.json

