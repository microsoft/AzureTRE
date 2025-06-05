data "azurerm_resource_group" "rg" {
  name = "rg-${var.tre_id}"
}

data "azurerm_key_vault" "key_vault" {
  name                = "kv-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_subnet" "app_gw_subnet" {
  name                 = "AppGwSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = data.azurerm_resource_group.rg.name
}

data "azurerm_user_assigned_identity" "resource_processor_vmss_id" {
  name                = "id-vmss-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_user_assigned_identity" "tre_encryption_identity" {
  count               = var.enable_cmk_encryption ? 1 : 0
  name                = local.encryption_identity_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_key_vault_key" "encryption_key" {
  count        = var.enable_cmk_encryption ? 1 : 0
  name         = local.cmk_name
  key_vault_id = var.key_store_id
}

data "azurerm_virtual_network" "core" {
  name                = "vnet-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_subnet" "sharedsubnet" {
  name                 = "SharedSubnet"
  virtual_network_name = data.azurerm_virtual_network.core.name
  resource_group_name  = data.azurerm_virtual_network.core.resource_group_name
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_private_dns_zone" "webcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.web.core.windows.net"]
  resource_group_name = data.azurerm_resource_group.rg.name
}
