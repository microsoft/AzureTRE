# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.46.0"
    }
  }
}

provider "azurerm" {
    features {}
}

resource "azurerm_resource_group" "core" {
  location  = var.location
  name      = "rg-${var.resource_name_prefix}-${var.environment}-${local.tre_id}"
  tags      = {
              project       = "Azure Trusted Research Environment"
              environment   = var.environment
              core_id       = "${var.resource_name_prefix}-${var.environment}-${local.tre_id}"
              source        = "https://github.com/microsoft/AzureTRE/"
  }
}

resource "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.resource_name_prefix}-${var.environment}-${local.tre_id}"
  resource_group_name = azurerm_resource_group.core.name
  location            = var.location
  retention_in_days   = 30
  sku                 = "pergb2018"
}

module "network" {
  source                = "./network"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  address_space         = var.address_space
}

module "appgateway" {
  source                = "./appgateway"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  app_gw_subnet         = module.network.app_gw
}

module "api-webapp" {
  source                = "./api-webapp"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  web_app_subnet        = module.network.web_app
  shared_subnet         = module.network.shared
  app_gw_subnet         = module.network.app_gw
  core_vnet             = module.network.core
  log_analytics_workspace_id = azurerm_log_analytics_workspace.tre.id
}

module "keyvault" {
  source                = "./keyvault"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  shared_subnet         = module.network.shared
  core_vnet             = module.network.core
  tenant_id             = data.azurerm_client_config.current.tenant_id
}

module "firewall" {
  source                = "./firewall"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  firewall_subnet       = module.network.azure_firewall
  shared_subnet         = module.network.shared
}

module "routetable" {
  source                = "./routetable"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  shared_subnet         = module.network.shared
  firewall_private_ip_address         = module.firewall.firewall_private_ip_address
}

module "acr" {
  source                = "./acr"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  core_vnet             = module.network.core
  shared_subnet         = module.network.shared
}

module "state-store" {
  source                         = "./state-store"
  resource_name_prefix           = var.resource_name_prefix
  environment                    = var.environment
  tre_id                         = local.tre_id
  location                       = var.location
  resource_group_name            = azurerm_resource_group.core.name
  shared_subnet                  = module.network.shared
  core_vnet                      = module.network.core
}
