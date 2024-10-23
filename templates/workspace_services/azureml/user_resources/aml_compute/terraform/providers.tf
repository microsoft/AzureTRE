terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.112.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "=1.15.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
  }
}

provider "azapi" {}
