output "shared_services_resource_group_name" {
  value = azurerm_resource_group.core.name
}

output "shared_services_vnet_name" {
  value = azurerm_virtual_network.core.name
}

output "log_analytics_name" {
  value = azurerm_log_analytics_workspace.tre.name
}

output "tre_id" {
  value = var.tre_id
}
