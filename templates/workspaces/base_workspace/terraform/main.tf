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

terraform {
  backend "azurerm" {
    key = "AzureTRE"
  }
}

resource "azurerm_resource_group" "ws" {
  location  = var.location
  name      = "rg-${var.core_id}-ws-${var.ws_id}"
  tags      = {
              project       = "Azure Trusted Research Environment"
              core_id       = var.core_id
              source        = "https://github.com/microsoft/AzureTRE/"
  }
}

module "network" {
  source                = "./network"
  ws_id                 = var.ws_id
  core_id               = var.core_id
  location              = var.location
  resource_group_name   = azurerm_resource_group.ws.name
  address_space         = var.address_space
  core_vnet             = local.core_vnet
  core_resource_group_name = local.core_resource_group_name
}
