terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.8.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "=3.2.1"
    }
  }
}
