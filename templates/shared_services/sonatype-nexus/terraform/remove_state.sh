#!/bin/bash
# This script works together with the import_state.sh script to manually remove the nexus state from the core deployment
# and import it into the nexus deployment. It's used for migration purposes only and will be removed when clients are all
# using the shared services model
echo "REMOVING STATE FOR NEXUS..."

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

remove_if_present module.nexus.azurerm_firewall_application_rule_collection.web_app_subnet_nexus
remove_if_present module.nexus.azurerm_private_endpoint.nexus_private_endpoint
remove_if_present module.nexus.azurerm_app_service_virtual_network_swift_connection.nexus-integrated-vnet
remove_if_present module.nexus.azurerm_app_service.nexus
#remove_if_present module.nexus.azurerm_storage_share.nexus
