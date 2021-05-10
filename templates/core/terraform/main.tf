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
  location = var.location
  name     =  "rg-${var.resource_name_prefix}-${var.environment}-${local.tre_id}"
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

module "api-webapp" {
  source                = "./api-webapp"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.core.name
  web_app_subnet        = module.network.web_app
  shared_subnet         = module.network.shared
  core_vnet             = module.network.core
  log_analytics_workspace_id = azurerm_log_analytics_workspace.tre.id
}

module "state-store" {
  source = "./state-store"
  name = "tre-${var.resource_name_prefix}"
  location = var.location
  resource_group_name = azurerm_resource_group.core.name
}