output "event_grid_status_changed_topic_endpoint" {
  value = azurerm_eventgrid_topic.status_changed.endpoint
}

output "event_grid_status_changed_topic_resource_id" {
  value = azurerm_eventgrid_topic.status_changed.id
}
