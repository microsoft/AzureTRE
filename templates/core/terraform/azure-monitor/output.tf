output "app_insights_instrumentation_key" {
  value = jsondecode(azurerm_resource_group_template_deployment.app_insights_core.output_content).instrumentationKey.value
}

output "app_insights_connection_string" {
  value = jsondecode(azurerm_resource_group_template_deployment.app_insights_core.output_content).connectionString.value
}

output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.core.id
}

output "log_analytics_workspace_name" {
  value = azurerm_log_analytics_workspace.core.name
}
