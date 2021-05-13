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
