terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.27.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.1.0"
    }
  }
}
