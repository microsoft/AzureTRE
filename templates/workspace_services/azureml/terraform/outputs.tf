output "azureml_workspace_name" {
  value = azapi_resource.aml_workspace.name
}

output "azureml_acr_id" {
  value = azurerm_container_registry.acr.id
}

output "azureml_storage_account_id" {
  value = azurerm_storage_account.aml.id
}

output "connection_uri" {
  value = "https://ml.azure.com/?wsid=${azapi_resource.aml_workspace.id}&tid=${var.arm_tenant_id}"
}

output "workspace_services_subnet_address_prefix" {
  value = data.azurerm_subnet.services.address_prefix
}

data "azurerm_network_service_tags" "storage_tag" {
  location        = azurerm_storage_account.aml.location
  service         = "Storage"
  location_filter = azurerm_storage_account.aml.location
}
output "storage_tag" {
  value = data.azurerm_network_service_tags.storage_tag.id
}
