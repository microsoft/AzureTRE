terraform {
  # In modules we should only specify the min version
  required_providers {
    azurerm = {
      source                = "hashicorp/azurerm"
      version               = ">= 4.24.0"
      configuration_aliases = [azurerm, azurerm.core]
    }
  }
}
