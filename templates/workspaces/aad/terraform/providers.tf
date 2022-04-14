terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.1.0"
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
      purge_soft_delete_on_destroy    = var.keyvault_purge_protection_enabled ? false : true
      recover_soft_deleted_key_vaults = false
    }
  }
  # These will be done by MSI
  # client_id = var.arm_client_id
  # client_secret = var.arm_client_secret
  # tenant_id = var.arm_tenant_id
  # subscription_id = var.arm_subscription_id
}
data "azurerm_subscription" "current" {}
data "azurerm_client_config" "current" {}

provider "azuread" {
  client_id     = var.api_client_id
  client_secret = var.api_client_secret
  tenant_id     = var.auth_tenant_id
}
