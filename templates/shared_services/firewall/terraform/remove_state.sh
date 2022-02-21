#!/bin/bash
# TODO: maybe rename script
# TODO: add a comment explaining wtf is going on

terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${MGMT_RESOURCE_GROUP_NAME}" \
    -backend-config="storage_account_name=${MGMT_STORAGE_ACCOUNT_NAME}" \
    -backend-config="container_name=${TERRAFORM_STATE_CONTAINER_NAME}" \
    -backend-config="key=${TRE_ID}"

function remove_if_present() {
  terraform state show $1
  if [[ $? -eq 0 ]]; then
    terraform state rm $1
  fi
}

remove_if_present azurerm_route_table.rt
remove_if_present azurerm_subnet_route_table_association.rt_resource_processor_subnet_association
remove_if_present azurerm_subnet_route_table_association.rt_shared_subnet_association
remove_if_present azurerm_subnet_route_table_association.rt_web_app_subnet_association
remove_if_present module.firewall
remove_if_present module.firewall.azurerm_public_ip.fwpip
remove_if_present module.firewall.azurerm_monitor_diagnostic_setting.firewall
remove_if_present module.firewall.azurerm_management_lock.fw
remove_if_present module.firewall.azurerm_firewall_network_rule_collection.web_app_subnet
remove_if_present module.firewall.azurerm_firewall_network_rule_collection.resource_processor_subnet
remove_if_present module.firewall.azurerm_firewall_network_rule_collection.general
remove_if_present module.firewall.azurerm_firewall_application_rule_collection.web_app_subnet
remove_if_present module.firewall.azurerm_firewall_application_rule_collection.shared_subnet
remove_if_present module.firewall.azurerm_firewall_application_rule_collection.resource_processor_subnet
remove_if_present module.firewall.azurerm_firewall.fw
remove_if_present azurerm_subnet_route_table_association.rt_web_app_subnet_association
remove_if_present azurerm_subnet_route_table_association.rt_shared_subnet_association
remove_if_present azurerm_subnet_route_table_association.rt_resource_processor_subnet_association
