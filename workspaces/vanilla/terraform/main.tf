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
  tenant_id       = var.azure_tenant_id
  subscription_id = var.azure_subscription_id
  client_id       = var.azure_service_principal_client_id
  client_secret   = var.azure_service_principal_password

  features {}
}

resource "azurerm_resource_group" "ws" {
  location = var.location
  name     = "rg-${var.core_id}-ws-${var.workspace_id}"
  tags     = {
    project = "Azure Trusted Research Environment"
    core_id = var.core_id
    source  = "https://github.com/microsoft/AzureTRE/"
  }
}

module "network" {
  source                   = "./network"
  workspace_id             = var.workspace_id
  core_id                  = var.core_id
  location                 = var.location
  resource_group_name      = azurerm_resource_group.ws.name
  address_space            = var.address_space
  core_vnet                = local.core_vnet
  core_resource_group_name = local.core_resource_group_name
}
