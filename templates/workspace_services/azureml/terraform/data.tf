data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_resource_group" "core" {
  name = "rg-${var.tre_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

resource "azurerm_application_insights" "ai" {
  name                = "ai-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  application_type    = "web"
  tags                = local.tre_workspace_service_tags

  lifecycle { ignore_changes = [tags] }
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "shared" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "SharedSubnet"
}

data "azurerm_route_table" "rt" {
  name                = "rt-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azureml" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.api.azureml.ms"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azuremlcert" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.cert.api.azureml.ms"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "notebooks" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.notebooks.azure.net"]
  resource_group_name = local.core_resource_group_name
}
