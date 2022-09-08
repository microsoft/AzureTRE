terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.97.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~>3.3.0"
    }
  }

  backend "azurerm" {
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_subnet" "web_apps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

data "azurerm_key_vault" "ws" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_app_service_plan" "workspace" {
  name                = "plan-${var.workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_log_analytics_workspace" "tre" {
  name                = "log-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.mgmt_acr_name
  resource_group_name = var.mgmt_resource_group_name
}

data "azurerm_storage_account" "mlflow" {
  name                = local.storage_name
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_private_dns_zone" "azurewebsites" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = local.core_resource_group_name
}
