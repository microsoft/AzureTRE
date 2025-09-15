data "azurerm_client_config" "core" {
  provider = azurerm.core
}

data "azurerm_client_config" "workspace" {
  provider = azurerm
}

data "azurerm_resource_group" "core" {
  provider = azurerm.core
  name     = local.core_resource_group_name
}

data "azurerm_virtual_network" "core" {
  provider            = azurerm.core
  name                = local.core_vnet
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "core_webapps" {
  provider             = azurerm.core
  name                 = "WebAppSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = "rg-${var.tre_id}"
}

data "azurerm_subnet" "shared" {
  provider             = azurerm.core
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "SharedSubnet"
}

data "azurerm_subnet" "bastion" {
  provider             = azurerm.core
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "AzureBastionSubnet"
}

data "azurerm_subnet" "resourceprocessor" {
  provider             = azurerm.core
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "ResourceProcessorSubnet"
}

data "azurerm_subnet" "airlockprocessor" {
  provider             = azurerm.core
  resource_group_name  = local.core_resource_group_name
  virtual_network_name = local.core_vnet
  name                 = "AirlockProcessorSubnet"
}

data "azurerm_firewall" "firewall" {
  provider            = azurerm.core
  name                = "fw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_route_table" "rt" {
  provider            = azurerm.core
  name                = "rt-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azurewebsites" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurewebsites.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "filecore" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.file.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "blobcore" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "dfscore" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.dfs.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "vaultcore" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.vaultcore.azure.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azurecr" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurecr.io"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azureml" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.api.azureml.ms"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azuremlcert" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.cert.api.azureml.ms"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "notebooks" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.notebooks.azure.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "mysql" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.mysql.database.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "postgres" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.postgres.database.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "azuresql" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.database.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "openai" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.openai.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "cognitiveservices" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.cognitiveservices.azure.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_public_ip" "app_gateway_ip" {
  provider            = azurerm.core
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "nexus" {
  provider            = azurerm.core
  name                = "nexus-${data.azurerm_public_ip.app_gateway_ip.fqdn}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "health" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azurehealthcareapis.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "dicom" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.dicom.azurehealthcareapis.com"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "databricks" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.azuredatabricks.net"]
  resource_group_name = local.core_resource_group_name
}
