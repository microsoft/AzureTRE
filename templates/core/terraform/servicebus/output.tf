output "connection_string" {
  value = azurerm_servicebus_namespace.sb.default_primary_connection_string
}

output "workspacequeue" {
  value = azurerm_servicebus_queue.workspacequeue.name
}

output "service_bus_deployment_status_update_queue" {
  value = azurerm_servicebus_queue.service_bus_deployment_status_update_queue.name
}
