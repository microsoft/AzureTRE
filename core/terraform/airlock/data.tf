data "local_file" "airlock_processor_version" {
  filename = "${path.root}/../../airlock_processor/_version.py"
}

data "azurerm_private_dns_zone" "eventgrid" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.eventgrid.azure.net"]
  resource_group_name = var.resource_group_name
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}

data "azurerm_monitor_diagnostic_categories" "eventgrid_custom_topics" {
  resource_id = azurerm_eventgrid_topic.airlock_notification.id
}

data "azurerm_monitor_diagnostic_categories" "eventgrid_system_topics" {
  resource_id = azurerm_eventgrid_system_topic.export_approved_blob_created.id
}
