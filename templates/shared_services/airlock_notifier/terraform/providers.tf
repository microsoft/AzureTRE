# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.113.0"
    }
    local = {
      source  = "hashicorp/local"
      version = "=2.5.1"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}
