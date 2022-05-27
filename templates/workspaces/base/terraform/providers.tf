terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.5.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "=2.20.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "=3.1.2"
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

data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

provider "azuread" {
  client_id     = var.auth_client_id
  client_secret = var.auth_client_secret
  tenant_id     = var.auth_tenant_id
}
