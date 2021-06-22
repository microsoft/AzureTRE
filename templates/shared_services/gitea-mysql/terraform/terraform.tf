# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.62.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}
