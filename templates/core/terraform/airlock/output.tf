output "event_grid_topic_endpoint" {
  value = azurerm_eventgrid_topic.status_changed.endpoint
}

output "event_grid_topic_resource_id" {
  value = azurerm_eventgrid_topic.status_changed.id
}
