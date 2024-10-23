terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.112.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "=2.0.1"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
  }
}

provider "azapi" {}
