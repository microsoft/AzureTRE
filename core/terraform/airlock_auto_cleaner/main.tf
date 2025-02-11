terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.58.0"
    }
    http = {
      source  = "hashicorp/http"
      version = "=3.4.5"
    }
  }
}

provider "azurerm" {
  skip_provider_registration = true
  features {}
}
