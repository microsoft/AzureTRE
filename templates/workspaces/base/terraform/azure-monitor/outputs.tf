output "app_insights_connection_string" {
  value = azurerm_application_insights.workspace.connection_string
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.workspace.id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.workspace.name
}
