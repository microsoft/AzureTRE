# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.61.0"
    }
  }
}

provider "azurerm" {
  tenant_id       = var.azure_tenant_id
  subscription_id = var.azure_subscription_id
  client_id       = var.azure_client_id
  client_secret   = var.azure_client_secret

  features {}
}

resource "azurerm_resource_group" "ws" {
  location = var.location
  name     = "rg-${local.workspace_resource_name_suffix}"
  tags = {
    project = "Azure Trusted Research Environment"
    tre_id = var.tre_id
    source  = "https://github.com/microsoft/AzureTRE/"
  }
}

module "network" {
  source                         = "./network"
  address_space                  = var.address_space
  core_resource_name_suffix      = local.core_resource_name_suffix
  workspace_resource_name_suffix = local.workspace_resource_name_suffix
  depends_on = [
    azurerm_resource_group.ws
  ]
}
