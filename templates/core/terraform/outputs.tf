output "core_id" {
  value = "${var.resource_name_prefix}-${var.environment}-${local.tre_id}"
}

output "core_resource_group_name" {
  value = azurerm_resource_group.core.name
}

output "log_analytics_name" {
  value = azurerm_log_analytics_workspace.tre.name
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
  value = module.keyvault.keyvault_name
}