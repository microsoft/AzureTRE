# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.4.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      # Don't purge secrets on destroy (this would fail due to purge protection being enabled on keyvault)
      purge_soft_deleted_secrets_on_destroy = false
      # When recreating a shared service, recover any previously soft deleted secrets
      recover_soft_deleted_secrets = true
    }
  }
}
