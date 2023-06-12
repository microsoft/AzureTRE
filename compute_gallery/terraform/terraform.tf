terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.60.0"
    }
  }

  # Backend initalised by terraform_wrapper.sh
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}
