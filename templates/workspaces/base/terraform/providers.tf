terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.27.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "= 3.3.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "= 2.3.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  subscription_id = local.workspace_subscription_id

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
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  storage_use_azuread = true
}

provider "azurerm" {
  alias = "core"
  features {
  }
}

provider "azuread" {
  client_id     = var.auth_client_id
  client_secret = var.auth_client_secret
  tenant_id     = var.auth_tenant_id
}

provider "azapi" {
}
