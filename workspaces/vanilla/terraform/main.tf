# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.61.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "ws" {
  location = var.location
  name     = "rg-${local.workspace_resource_name_suffix}"
  tags = {
    project = "Azure Trusted Research Environment"
    tre_id  = var.tre_id
    source  = "https://github.com/microsoft/AzureTRE/"
  }

  lifecycle { ignore_changes = [ tags ] }
}

module "network" {
  source                   = "./network"
  workspace_id             = var.workspace_id
  tre_id                   = var.tre_id
  location                 = var.location
  resource_group_name      = azurerm_resource_group.ws.name
  address_space            = var.address_space
  core_vnet                = local.core_vnet
  core_resource_group_name = local.core_resource_group_name
}
