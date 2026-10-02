terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.60.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.8.0"
    }
    fabric = {
      source  = "microsoft/fabric"
      version = "= 1.14.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.9.0"
    }
  }
  backend "azurerm" {
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy               = false
      purge_soft_deleted_secrets_on_destroy      = false
      purge_soft_deleted_certificates_on_destroy = false
      purge_soft_deleted_keys_on_destroy         = false
      recover_soft_deleted_key_vaults            = true
      recover_soft_deleted_secrets               = true
      recover_soft_deleted_certificates          = true
      recover_soft_deleted_keys                  = true
    }
  }
  storage_use_azuread = true
}

provider "azurerm" {
  alias = "core"
  features {}
}

provider "azapi" {}

provider "fabric" {
  tenant_id     = var.arm_tenant_id
  client_id     = var.arm_client_id
  client_secret = var.arm_use_msi ? null : var.arm_client_secret
  use_msi       = var.arm_use_msi
  preview       = true
  # NOTE: use_workspace_private_link_endpoint is intentionally disabled.
  # The resource processor VMSS runs in the core VNet and cannot reliably
  # route through the workspace private endpoint, causing context deadline
  # exceeded errors on Fabric API calls. End-user access via the PE is
  # configured separately through the workspace private endpoint resources.
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=0.2.0"
  arm_environment = var.arm_environment
}
