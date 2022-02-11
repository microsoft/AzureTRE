#!/bin/bash
# TODO: maybe rename script
# TODO: add a comment explaining wtf is going on

export TF_VAR_docker_registry_server="$TF_VAR_acr_name.azurecr.io"
export TF_VAR_docker_registry_username=$TF_VAR_acr_name
export TF_VAR_docker_registry_password=$(az acr credential show --name ${TF_VAR_acr_name} --query passwords[0].value -o tsv | sed 's/"//g')

LOG_FILE="tmp$$.log"

# TODO: what if isn't there?
# Firewall
../../../../devops/scripts/terraform_wrapper.sh \
  -g $TF_VAR_mgmt_resource_group_name \
  -s $TF_VAR_mgmt_storage_account_name \
  -n $TF_VAR_terraform_state_container_name \
  -k ${TRE_ID} \
  -l ${LOG_FILE} \
  -c "terraform state rm azurerm_route_table.rt && \
    terraform state rm azurerm_subnet_route_table_association.rt_resource_processor_subnet_association && \
    terraform state rm azurerm_subnet_route_table_association.rt_shared_subnet_association && \
    terraform state rm azurerm_subnet_route_table_association.rt_web_app_subnet_association && \
    terraform state rm module.firewall"

# terraform state rm azurerm_route_table.rt
# terraform state rm azurerm_subnet_route_table_association.rt_resource_processor_subnet_association
# terraform state rm azurerm_subnet_route_table_association.rt_shared_subnet_association
# terraform state rm azurerm_subnet_route_table_association.rt_web_app_subnet_association
# terraform state rm module.firewall
# module.firewall.azurerm_firewall.fw
# module.firewall.azurerm_firewall_application_rule_collection.resource_processor_subnet
# module.firewall.azurerm_firewall_application_rule_collection.shared_subnet
# module.firewall.azurerm_firewall_application_rule_collection.web_app_subnet
# module.firewall.azurerm_firewall_network_rule_collection.general
# module.firewall.azurerm_firewall_network_rule_collection.resource_processor_subnet
# module.firewall.azurerm_firewall_network_rule_collection.web_app_subnet
# module.firewall.azurerm_management_lock.fw
# module.firewall.azurerm_monitor_diagnostic_setting.firewall
# module.firewall.azurerm_public_ip.fwpip

# Gitea
# module.gitea[0].azurerm_app_service.gitea
# module.gitea[0].azurerm_app_service_virtual_network_swift_connection.gitea-integrated-vnet
# module.gitea[0].azurerm_firewall_application_rule_collection.web_app_subnet_gitea
# module.gitea[0].azurerm_key_vault_access_policy.gitea_policy
# module.gitea[0].azurerm_key_vault_secret.db_password
# module.gitea[0].azurerm_key_vault_secret.gitea_password
# module.gitea[0].azurerm_monitor_diagnostic_setting.webapp_gitea
# module.gitea[0].azurerm_mysql_database.gitea
# module.gitea[0].azurerm_mysql_server.gitea
# module.gitea[0].azurerm_private_endpoint.gitea_private_endpoint
# module.gitea[0].azurerm_private_endpoint.private-endpoint
# module.gitea[0].azurerm_role_assignment.gitea_acrpull_role
# module.gitea[0].azurerm_storage_share.gitea
# module.gitea[0].azurerm_user_assigned_identity.gitea_id
# module.gitea[0].null_resource.webapp_vault_access_identity
# module.gitea[0].random_password.gitea_passwd
# module.gitea[0].random_password.password

# Nexus
# module.nexus[0].azurerm_app_service.nexus
# module.nexus[0].azurerm_app_service_virtual_network_swift_connection.nexus-integrated-vnet
# module.nexus[0].azurerm_firewall_application_rule_collection.web_app_subnet_nexus
# module.nexus[0].azurerm_monitor_diagnostic_setting.nexus
# module.nexus[0].azurerm_private_endpoint.nexus_private_endpoint
# module.nexus[0].azurerm_storage_share.nexus
# module.nexus[0].null_resource.upload_nexus_props
