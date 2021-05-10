output "core_resource_group_name" {
  value = azurerm_resource_group.core.name
}

output "log_analytics_name" {
  value = azurerm_log_analytics_workspace.tre.name
}
