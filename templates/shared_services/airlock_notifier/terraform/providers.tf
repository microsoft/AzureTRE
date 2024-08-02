# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.113.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "=1.14.0"
    }
  }
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}
