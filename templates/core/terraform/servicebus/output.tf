output "connection_string" {
  value = azurerm_servicebus_namespace.sb.default_primary_connection_string
}

output "workspacequeue" {
  value = azurerm_servicebus_queue.workspacequeue.name
}