#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

terraform_wrapper_path="../../devops/scripts/terraform_wrapper.sh"

# This variables are loaded in for us
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

echo "*** Migrating TF Resources... ***"
# terraform show might fail if provider schema has changed. Since we don't call apply at this stage a refresh is needed
terraform refresh

# 1. Check we have a root_module in state
# 2. Grab the Resource ID
# 3. Delete the old resource from state
# 4. Import the new resource type in using the existing Azure Resource ID

terraform_show_json=$(terraform show -json)

# azurerm_app_service_plan -> azurerm_service_plan
core_app_service_plan_id=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_app_service_plan.core") | .values.id')
if [ -n "${core_app_service_plan_id}" ]; then
  echo "Migrating ${core_app_service_plan_id}"
  terraform state rm azurerm_app_service_plan.core
  if [[ $(az resource list --query "[?id=='${core_app_service_plan_id}'] | length(@)") == 0 ]];
  then
    echo "The resource doesn't exist on Azure. Skipping importing it back to state."
  else
    terraform import azurerm_service_plan.core "${core_app_service_plan_id}"
  fi
fi

# azurerm_app_service -> azurerm_linux_web_app
api_app_service_id=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_app_service.api") | .values.id')
if [ -n "${api_app_service_id}" ]; then
  echo "Migrating ${api_app_service_id}"
  terraform state rm azurerm_app_service.api
  if [[ $(az resource list --query "[?id=='${api_app_service_id}'] | length(@)") == 0 ]];
  then
    echo "The resource doesn't exist on Azure. Skipping importing it back to state."
  else
    terraform import azurerm_linux_web_app.api "${api_app_service_id}"
  fi
fi

# app insights via -> native tf resource
app_insights_via_arm=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.child_modules != null) .values.root_module.child_modules[] | select (.address=="module.azure_monitor") | .resources[] | select(.address=="module.azure_monitor.azurerm_resource_group_template_deployment.app_insights_core") | .values.id')
if [ -n "${app_insights_via_arm}" ]; then
  echo "Migrating ${app_insights_via_arm}"

  PLAN_FILE="tfplan$$"
  TS=$(date +"%s")
  LOG_FILE="${TS}-tre-core-migrate.log"

  # This variables are loaded in for us
  # shellcheck disable=SC2154
  "${terraform_wrapper_path}" \
    -g "${TF_VAR_mgmt_resource_group_name}" \
    -s "${TF_VAR_mgmt_storage_account_name}" \
    -n "${TF_VAR_terraform_state_container_name}" \
    -k "${TRE_ID}" \
    -l "${LOG_FILE}" \
    -c "terraform plan -target module.azure_monitor.azurerm_resource_group_template_deployment.app_insights_core -target module.azure_monitor.azurerm_resource_group_template_deployment.ampls_core -out ${PLAN_FILE} && \
    terraform apply -input=false -auto-approve ${PLAN_FILE}"
fi

# support downgrading core app service plan
core_plan=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_service_plan.core") | .values.id')
api_diag=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_monitor_diagnostic_setting.webapp_api") | .values.id')
if [ -n "${core_plan}" ] && [ -n "${api_diag}" ]; then
  set +o errexit
  terraform plan -target "azurerm_service_plan.core" -detailed-exitcode
  plan_exit_code=$?
  set -o errexit

  if [ "${plan_exit_code}" == "2" ]; then
    echo "Migrating ${api_diag}"
    PLAN_FILE="tfplan$$"
    TS=$(date +"%s")
    LOG_FILE="${TS}-tre-core-migrate.log"

    # This variables are loaded in for us
    # shellcheck disable=SC2154
    "${terraform_wrapper_path}" \
      -g "${TF_VAR_mgmt_resource_group_name}" \
      -s "${TF_VAR_mgmt_storage_account_name}" \
      -n "${TF_VAR_terraform_state_container_name}" \
      -k "${TRE_ID}" \
      -l "${LOG_FILE}" \
      -c "terraform plan -destroy -target azurerm_monitor_diagnostic_setting.webapp_api -out ${PLAN_FILE} && \
      terraform apply -input=false -auto-approve ${PLAN_FILE}"
  fi
fi

# remove app insights profiler storage account
app_insights_byo_storage=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.child_modules != null) .values.root_module.child_modules[] | select (.address=="module.azure_monitor") | .resources[] | select(.address=="module.azure_monitor.azurerm_resource_group_template_deployment.app_insights_byo_storage") | .values.id')
if [ -n "${app_insights_byo_storage}" ]; then
  echo "Removing state of app_insights_byo_storage"
  terraform state rm module.azure_monitor.azurerm_resource_group_template_deployment.app_insights_byo_storage
fi

# airlock inline vnet integration (instead of via swift)
airlock_vnet_integration=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.child_modules != null) .values.root_module.child_modules[] | select (.address=="module.airlock_resources") | .resources[] | select(.address=="module.airlock_resources.azurerm_app_service_virtual_network_swift_connection.airlock_integrated_vnet") | .values.id')
if [ -n "${airlock_vnet_integration}" ]; then
  echo "Migrating ${airlock_vnet_integration}"

  PLAN_FILE="tfplan$$"
  TS=$(date +"%s")
  LOG_FILE="${TS}-tre-core-migrate.log"

  # This variables are loaded in for us
  # shellcheck disable=SC2154
  "${terraform_wrapper_path}" \
    -g "${TF_VAR_mgmt_resource_group_name}" \
    -s "${TF_VAR_mgmt_storage_account_name}" \
    -n "${TF_VAR_terraform_state_container_name}" \
    -k "${TRE_ID}" \
    -l "${LOG_FILE}" \
    -c "terraform plan -target module.airlock_resources.azurerm_app_service_virtual_network_swift_connection.airlock_integrated_vnet -out ${PLAN_FILE} && \
    terraform apply -input=false -auto-approve ${PLAN_FILE}"
fi

# api inline vnet integration (instead of via swift)
api_vnet_integration=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_app_service_virtual_network_swift_connection.api_integrated_vnet") | .values.id')
if [ -n "${api_vnet_integration}" ]; then
  echo "Migrating ${api_vnet_integration}"

  PLAN_FILE="tfplan$$"
  TS=$(date +"%s")
  LOG_FILE="${TS}-tre-core-migrate.log"

  # This variables are loaded in for us
  # shellcheck disable=SC2154
  "${terraform_wrapper_path}" \
    -g "${TF_VAR_mgmt_resource_group_name}" \
    -s "${TF_VAR_mgmt_storage_account_name}" \
    -n "${TF_VAR_terraform_state_container_name}" \
    -k "${TRE_ID}" \
    -l "${LOG_FILE}" \
    -c "terraform plan -target azurerm_app_service_virtual_network_swift_connection.api_integrated_vnet -out ${PLAN_FILE} && \
    terraform apply -input=false -auto-approve ${PLAN_FILE}"
fi

# support changing the resource processor subnet size
rp_subnet=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.child_modules != null) .values.root_module.child_modules[] | select (.address=="module.network") | .resources[] | select(.address=="module.network.azurerm_subnet.resource_processor") | .values.id')
if [ -n "${rp_subnet}" ]; then
  set +o errexit
  terraform plan -target "module.network.azurerm_subnet.resource_processor" -detailed-exitcode
  plan_exit_code=$?
  set -o errexit

  if [ "${plan_exit_code}" == "2" ]; then
    echo "Migrating ${rp_subnet}"
    PLAN_FILE="tfplan$$"
    TS=$(date +"%s")
    LOG_FILE="${TS}-tre-core-migrate-rp-subnet.log"

    # This variables are loaded in for us
    # shellcheck disable=SC2154
    "${terraform_wrapper_path}" \
      -g "${TF_VAR_mgmt_resource_group_name}" \
      -s "${TF_VAR_mgmt_storage_account_name}" \
      -n "${TF_VAR_terraform_state_container_name}" \
      -k "${TRE_ID}" \
      -l "${LOG_FILE}" \
      -c "terraform plan -destroy -target module.resource_processor_vmss_porter[0].azurerm_linux_virtual_machine_scale_set.vm_linux \
      -target azurerm_private_endpoint.sbpe \
      -target azurerm_private_endpoint.mongo \
      -out ${PLAN_FILE} && \
      terraform apply -input=false -auto-approve ${PLAN_FILE}"
  fi
fi

# DNS Zones migration. We can't use a moved block due the the vars being used.
nexus_dns_zone=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.child_modules != null) .values.root_module.child_modules[] | select (.address=="module.network") | .resources[] | select(.address=="module.network.azurerm_private_dns_zone.nexus") | .values.id')
if [ -n "${nexus_dns_zone}" ]; then
  terraform state rm module.network.azurerm_private_dns_zone.nexus
  terraform import azurerm_private_dns_zone.non_core[\""nexus-${TRE_ID}.${LOCATION}.cloudapp.azure.com"\"] "${nexus_dns_zone}"
fi

# this isn't a classic migration, but impacts how terraform handles the deployment in the next phase
state_store_serverless=$(echo "${terraform_show_json}" \
  | jq 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_cosmosdb_account.tre_db_account") | any(.values.capabilities[]; .name=="EnableServerless")')
# false = resource EXITS in the state WITHOUT the serverless capability.
# true = exists with the capability, empty value = resource doesn't exist.
if [ "${state_store_serverless}" == "false" ]; then
  echo "Identified CosmosDB with defined throughput."
  TF_VAR_is_cosmos_defined_throughput="true"
  export TF_VAR_is_cosmos_defined_throughput
fi

echo "*** Migration is done. ***"
