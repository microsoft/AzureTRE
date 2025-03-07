terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=4.14.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = ">= 2.20"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.3.0"
    }
  }
}
