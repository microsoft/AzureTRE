data "azurerm_virtual_network" "core" {
  name                = local.core_vnet
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "core_webapps" {
  name                 = "WebAppSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = "rg-${var.tre_id}"
}

data "azurerm_subnet" "shared" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "SharedSubnet"
}

data "azurerm_subnet" "bastion" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "AzureBastionSubnet"
}

data "azurerm_subnet" "resourceprocessor" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "ResourceProcessorSubnet"
}

data "azurerm_subnet" "airlockprocessor" {
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "AirlockProcessorSubnet"
}

data "azurerm_route_table" "rt" {
  name                = "rt-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azurewebsites" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "filecore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.file.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "dfscore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.dfs.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "vaultcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.vaultcore.azure.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azurecr" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurecr.io"]
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

data "azurerm_private_dns_zone" "mysql" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.mysql.database.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "postgres" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.postgres.database.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_public_ip" "app_gateway_ip" {
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "nexus" {
  name                = "nexus-${data.azurerm_public_ip.app_gateway_ip.fqdn}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "health" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurehealthcareapis.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "dicom" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.dicom.azurehealthcareapis.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "databricks" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azuredatabricks.net"]
  resource_group_name = local.core_resource_group_name
}
