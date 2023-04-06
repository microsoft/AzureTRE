output "azureml_workspace_name" {
  value = azurerm_machine_learning_workspace.aml_workspace.name
}

output "azureml_acr_id" {
  value = azurerm_container_registry.acr.id
}

output "azureml_acr_name" {
  value = azurerm_container_registry.acr.name
}

output "core_location" {
  value = data.azurerm_resource_group.core.location
}

output "azureml_storage_account_id" {
  value = azurerm_storage_account.aml.id
}

output "connection_uri" {
  value = var.is_exposed_externally ? "https://ml.azure.com/?wsid=${azurerm_machine_learning_workspace.aml_workspace.id}&tid=${var.arm_tenant_id}" : ""
}

output "internal_connection_uri" {
  value = var.is_exposed_externally ? "" : "https://ml.azure.com/?wsid=${azurerm_machine_learning_workspace.aml_workspace.id}&tid=${var.arm_tenant_id}"
}

output "workspace_address_spaces" {
  value = data.azurerm_virtual_network.ws.address_space
}

output "aml_subnet_address_prefixes" {
  value = azurerm_subnet.aml.address_prefixes
}

data "azurerm_network_service_tags" "storage_tag" {
  location        = azurerm_storage_account.aml.location
  service         = "Storage"
  location_filter = azurerm_storage_account.aml.location
}

data "azurerm_network_service_tags" "mcr_tag" {
  location        = azurerm_storage_account.aml.location
  service         = "MicrosoftContainerRegistry"
  location_filter = azurerm_storage_account.aml.location
}

data "azurerm_network_service_tags" "batch_tag" {
  location        = azurerm_storage_account.aml.location
  service         = "BatchNodeManagement"
  location_filter = azurerm_storage_account.aml.location
}

output "storage_tag" {
  value = data.azurerm_network_service_tags.storage_tag.id
}

output "mcr_tag" {
  value = data.azurerm_network_service_tags.mcr_tag.id
}

output "batch_tag" {
  value = data.azurerm_network_service_tags.batch_tag.id
}
