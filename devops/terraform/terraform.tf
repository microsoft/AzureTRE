terraform {
  required_version = ">= 1.2.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "3.45.0"
    }
  }
}
