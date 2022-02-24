#!/bin/bash
# This script works together with the import_state.sh script to manually remove the gitea state from the core deployment
# and import it into the gitea deployment. It's used for migration purposes only and will be removed when clients are all
# using the shared services model
echo "REMOVING STATE FOR GITEA..."

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
    terraform state rm $2
  else
    echo " not present"
  fi
}

remove_if_present "module.gitea\[0\].azurerm_key_vault_secret.db_password" module.gitea[0].azurerm_key_vault_secret.db_password
remove_if_present "module.gitea\[0\].azurerm_private_endpoint.private-endpoint" module.gitea[0].azurerm_private_endpoint.private-endpoint
remove_if_present "module.gitea\[0\].azurerm_mysql_database.gitea" module.gitea[0].azurerm_mysql_database.gitea
remove_if_present "module.gitea\[0\].azurerm_mysql_server.gitea" module.gitea[0].azurerm_mysql_server.gitea
remove_if_present "module.gitea\[0\].random_password.password" module.gitea[0].random_password.password
remove_if_present "module.gitea\[0\].azurerm_storage_share.gitea" module.gitea[0].azurerm_storage_share.gitea
remove_if_present "module.gitea\[0\].azurerm_key_vault_secret.gitea_password" module.gitea[0].azurerm_key_vault_secret.gitea_password
remove_if_present "module.gitea\[0\].azurerm_app_service_virtual_network_swift_connection.gitea-integrated-vnet" module.gitea[0].azurerm_app_service_virtual_network_swift_connection.gitea-integrated-vnet
remove_if_present "module.gitea\[0\].azurerm_private_endpoint.gitea_private_endpoint" module.gitea[0].azurerm_private_endpoint.gitea_private_endpoint
remove_if_present "module.gitea\[0\].azurerm_app_service.gitea" module.gitea[0].azurerm_app_service.gitea
remove_if_present "module.gitea\[0\].azurerm_user_assigned_identity.gitea_id" module.gitea[0].azurerm_user_assigned_identity.gitea_id
remove_if_present "module.gitea\[0\].random_password.gitea_passwd" module.gitea[0].random_password.gitea_passwd
remove_if_present "module.gitea\[0\].azurerm_firewall_application_rule_collection.web_app_subnet_gitea" module.gitea[0].azurerm_firewall_application_rule_collection.web_app_subnet_gitea
