output "azureml_workspace_name" {
  value = azapi_resource.aml_workspace.output.name
}

output "azureml_acr_id" {
  value = azurerm_container_registry.acr.id
}

output "azureml_storage_account_id" {
  value = azurerm_storage_account.aml.id
}

output "aml_fqdn" {
  value = regex("(?:(?P<scheme>[^:/?#]+):)?(?://(?P<fqdn>[^/?#:]*))?", module.terraform_azurerm_environment_configuration.aml_studio_endpoint).fqdn
}

output "connection_uri" {
  value = format("%s/?wsid=%s&tid=%s", module.terraform_azurerm_environment_configuration.aml_studio_endpoint, azapi_resource.aml_workspace.output.id, var.arm_tenant_id)
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
  value = data.azurerm_network_service_tags.storage_tag.name
}

output "mcr_tag" {
  value = data.azurerm_network_service_tags.mcr_tag.name
}

output "batch_tag" {
  value = data.azurerm_network_service_tags.batch_tag.name
}
