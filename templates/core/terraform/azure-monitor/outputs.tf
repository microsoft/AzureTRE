output "app_insights_connection_string" {
  value = azurerm_application_insights.core.connection_string
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.core.id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.core.name
}

output "log_analytics_workspace_primary_key" {
  value = azurerm_log_analytics_workspace.core.primary_shared_key
}

output "log_analytics_workspace_workspace_id" {
  value = azurerm_log_analytics_workspace.core.workspace_id
}
