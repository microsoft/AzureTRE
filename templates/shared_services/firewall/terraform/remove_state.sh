#!/bin/bash
# This script works together with the import_state.sh script to manually remove the firewall state from the core deployment
# and import it into the firewall deployment. It's used for migration purposes only and will be removed when clients are all
# using the shared services model
echo "REMOVING STATE FOR FIREWALL..."

set -e

terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

tf_state_list="$(terraform state list)"
function remove_if_present() {
  echo -n "Checking $1 ..."
  found=$(echo "$tf_state_list" | grep -q ^$1$; echo $?)

  if [[ $found -eq 0 ]]; then
    echo " removing"
    terraform state rm $1
  else
    echo " not present"
  fi
}

remove_if_present azurerm_route_table.rt
remove_if_present azurerm_subnet_route_table_association.rt_resource_processor_subnet_association
remove_if_present azurerm_subnet_route_table_association.rt_shared_subnet_association
remove_if_present azurerm_subnet_route_table_association.rt_web_app_subnet_association
remove_if_present module.firewall
remove_if_present module.firewall.azurerm_public_ip.fwpip
remove_if_present module.firewall.azurerm_monitor_diagnostic_setting.firewall
remove_if_present module.firewall.azurerm_firewall_network_rule_collection.web_app_subnet
remove_if_present module.firewall.azurerm_firewall_network_rule_collection.resource_processor_subnet
remove_if_present module.firewall.azurerm_firewall_network_rule_collection.general
remove_if_present module.firewall.azurerm_firewall_application_rule_collection.web_app_subnet
remove_if_present module.firewall.azurerm_firewall_application_rule_collection.shared_subnet
remove_if_present module.firewall.azurerm_firewall_application_rule_collection.resource_processor_subnet
remove_if_present module.firewall.azurerm_firewall.fw
