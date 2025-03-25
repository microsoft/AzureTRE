output "event_grid_status_changed_topic_endpoint" {
  value = azurerm_eventgrid_topic.status_changed.endpoint
}

output "event_grid_airlock_notification_topic_endpoint" {
  value = azurerm_eventgrid_topic.airlock_notification.endpoint
}

output "service_bus_step_result_queue" {
  value = azurerm_servicebus_queue.step_result.name
}

output "event_grid_status_changed_topic_resource_id" {
  value = azurerm_eventgrid_topic.status_changed.id
}

output "event_grid_airlock_notification_topic_resource_id" {
  value = azurerm_eventgrid_topic.airlock_notification.id
}

output "airlock_malware_scan_result_topic_name" {
  value = local.scan_result_topic_name
}
