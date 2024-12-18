terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">=3.112.0"
    }
    fabric = {
      source  = "microsoft/fabric"
      version = "0.1.0-beta.5"
    }
    azapi = {
      source  = "Azure/azapi"
      version = ">=1.15.0"
    }
  }
}
