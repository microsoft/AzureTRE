# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.99.0"
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

  lifecycle { ignore_changes = [tags] }
}
