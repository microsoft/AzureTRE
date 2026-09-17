data "local_file" "airlock_processor_version" {
  filename = "${path.root}/../../airlock_processor/_version.py"
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = split("/", var.blob_core_dns_zone_id)[8]
  resource_group_name = var.resource_group_name
}

data "azurerm_monitor_diagnostic_categories" "eventgrid_custom_topics" {
  resource_id = azurerm_eventgrid_topic.airlock_notification.id
}

data "azurerm_monitor_diagnostic_categories" "eventgrid_system_topics" {
  resource_id = azurerm_eventgrid_system_topic.airlock_blob_created.id
}
