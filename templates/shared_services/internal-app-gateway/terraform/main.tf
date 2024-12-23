terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 3.117"
    }
  }

  backend "azurerm" {}
}


provider "azurerm" {
  features {}
}
