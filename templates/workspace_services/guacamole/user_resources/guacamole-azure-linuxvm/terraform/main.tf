# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.112.0"
    }
    template = {
      source  = "hashicorp/template"
      version = "=2.2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "=3.4.3"
    }
  }
  backend "azurerm" {
  }
}


provider "azurerm" {
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
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_resource_group" "core" {
  name = "rg-${var.tre_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_resource_group.ws.name
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_linux_web_app" "guacamole" {
  name                = "guacamole-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_public_ip" "app_gateway_ip" {
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.core.name
}
