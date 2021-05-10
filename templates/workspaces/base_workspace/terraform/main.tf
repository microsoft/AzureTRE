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

resource "azurerm_resource_group" "ws" {
  location  = var.location
  name      = "rg-ws-${var.resource_name_prefix}-${var.environment}-${local.tre_id}"
  tags      = {
              environment   = "Azure Trusted Research Environment"
              Source        = "https://github.com/microsoft/AzureTRE/"
  }
}

module "network" {
  source                = "./network"
  resource_name_prefix  = var.resource_name_prefix
  environment           = var.environment
  tre_id                = local.tre_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.ws.name
  address_space         = var.address_space
  core_vnet             = var.core_vnet
  core_resource_group_name = var.core_resource_group_name
}
