terraform {
  # In modules we should only specify the min version
  required_providers {
    azapi = {
      source  = "Azure/azapi"
      version = ">= 2.8.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.27.0"
    }
  }
}
