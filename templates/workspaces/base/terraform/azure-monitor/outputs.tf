output "app_insights_connection_string" {
  value = jsondecode(azurerm_resource_group_template_deployment.app_insights_workspace.output_content).connectionString.value
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.workspace.id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.workspace.name
}
