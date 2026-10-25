# Azure Provider source and version being used
terraform {
  required_providers {
    # Before 5.3.0, a FHIR create that Azure reports as Accepted fails, and the state does not get the service.
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.11.0"
    }
    # Versions before 2.9.0 fail each update when Terraform is earlier than 1.12.
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.9.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  # Version 5 registers no resource providers by default. Keep the registrations of version 4.
  resource_provider_registrations = "legacy"
  features {
    key_vault {
      # Don't purge on destroy (this would fail due to purge protection being enabled on keyvault)
      purge_soft_delete_on_destroy               = false
      purge_soft_deleted_secrets_on_destroy      = false
      purge_soft_deleted_certificates_on_destroy = false
      purge_soft_deleted_keys_on_destroy         = false
      # When recreating an environment, recover any previously soft deleted secrets - set to true by default
      recover_soft_deleted_key_vaults   = true
      recover_soft_deleted_secrets      = true
      recover_soft_deleted_certificates = true
      recover_soft_deleted_keys         = true
    }
  }
  storage_use_azuread = true
}

provider "azapi" {}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.7.0"
  arm_environment = var.arm_environment
}
