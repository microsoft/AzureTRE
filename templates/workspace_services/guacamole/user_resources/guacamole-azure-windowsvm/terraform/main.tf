# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source                = "hashicorp/azurerm"
      version               = "= 4.27.0"
      configuration_aliases = [azurerm.core]
    }
    random = {
      source  = "hashicorp/random"
      version = "= 3.7.2"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "= 3.3.0"
    }
  }
  backend "azurerm" {
  }
}

provider "azurerm" {
  subscription_id = coalesce(var.workspace_subscription_id, data.azurerm_client_config.current.subscription_id)

  features {
    virtual_machine {
      skip_shutdown_and_force_delete = true
      delete_os_disk_on_deletion     = true
    }
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
