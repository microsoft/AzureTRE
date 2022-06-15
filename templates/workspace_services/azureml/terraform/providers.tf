terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.99.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "=0.3.0"
    }

  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
  }
}

provider "azapi" {
}

data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

