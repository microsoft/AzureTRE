terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.117.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"
    }
  }
}


provider "azurerm" {
  features {
     recovery_services_vault {
       purge_protected_items_from_vault_on_destroy = true
     }
  }
}
