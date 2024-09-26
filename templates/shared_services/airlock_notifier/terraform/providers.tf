# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.112.0"
    }
  }
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}
