# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.64.0"
    }
  }
}

provider "azurerm" {
    features {}
}

module "storage" {
  source                = "./storage"
  workspace_id          = var.workspace_id
  location              = var.location
  service_id            = local.service_id
}
