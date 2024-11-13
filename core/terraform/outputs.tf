output "core_resource_group_name" {
  value = azurerm_resource_group.core.name
}

output "core_resource_group_location" {
  value = azurerm_resource_group.core.location
}

output "log_analytics_name" {
  value = module.azure_monitor.log_analytics_workspace_name
}

output "azure_tre_fqdn" {
  value = module.appgateway.app_gateway_fqdn
}

output "app_gateway_name" {
  value = module.appgateway.app_gateway_name
}

output "static_web_storage" {
  value = module.appgateway.static_web_storage
}

output "keyvault_name" {
  value = azurerm_key_vault.kv.name
}

output "keyvault_uri" {
  value = azurerm_key_vault.kv.vault_uri
}

output "keyvault_resource_id" {
  value = azurerm_key_vault.kv.id
}

output "service_bus_resource_id" {
  value = azurerm_servicebus_namespace.sb.id
}

output "service_bus_namespace_fqdn" {
  value = local.service_bus_namespace_fqdn
}

output "service_bus_workspace_queue" {
  value = azurerm_servicebus_queue.workspacequeue.name
}

output "service_bus_deployment_status_queue" {
  value = azurerm_servicebus_queue.service_bus_deployment_status_update_queue.name
}

output "state_store_resource_id" {
  value = azurerm_cosmosdb_account.tre_db_account.id
}

output "cosmosdb_mongo_resource_id" {
  value = azurerm_cosmosdb_account.mongo.id
}

output "state_store_endpoint" {
  value = azurerm_cosmosdb_account.tre_db_account.endpoint
}

output "cosmosdb_mongo_endpoint" {
  value     = azurerm_cosmosdb_account.mongo.primary_sql_connection_string
  sensitive = true
}

output "state_store_account_name" {
  value = azurerm_cosmosdb_account.tre_db_account.name
}

output "cosmosdb_mongo_account_name" {
  value = azurerm_cosmosdb_account.mongo.name
}

output "app_insights_connection_string" {
  value     = module.azure_monitor.app_insights_connection_string
  sensitive = true
}

# Make admin deployment values available in private.env output for easier local debugging
output "mgmt_storage_account_name" {
  value = var.mgmt_storage_account_name
}

output "mgmt_resource_group_name" {
  value = var.mgmt_resource_group_name
}

output "terraform_state_container_name" {
  value = var.terraform_state_container_name
}

output "registry_server" {
  value = local.docker_registry_server
}

output "event_grid_status_changed_topic_endpoint" {
  value = module.airlock_resources.event_grid_status_changed_topic_endpoint
}

output "event_grid_airlock_notification_topic_endpoint" {
  value = module.airlock_resources.event_grid_airlock_notification_topic_endpoint
}

output "event_grid_status_changed_topic_resource_id" {
  value = module.airlock_resources.event_grid_status_changed_topic_resource_id
}

output "event_grid_airlock_notification_topic_resource_id" {
  value = module.airlock_resources.event_grid_airlock_notification_topic_resource_id
}

output "service_bus_step_result_queue" {
  value = module.airlock_resources.service_bus_step_result_queue
}
