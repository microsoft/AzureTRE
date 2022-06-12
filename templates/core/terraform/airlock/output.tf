output "event_grid_topic_endpoint" {
  value = azurerm_eventgrid_topic.status_changed.endpoint
}

output "event_grid_access_key" {
  value = azurerm_eventgrid_topic.status_changed.primary_access_key
}
