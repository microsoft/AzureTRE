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
  features {}
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
data "azuread_client_config" "current" {}
