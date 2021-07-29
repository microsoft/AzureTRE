# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.61.0"
    }
  }
  backend "azurerm" {
  }
}


provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${var.workspace_id}"
  resource_group_name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_subnet" "web_apps" {
  name                 = "WebAppsSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  =  data.azurerm_resource_group.ws.name
}

data "azurerm_private_dns_zone" "azurewebsites" {
  name                = "privatelink.azurewebsites.net"
  resource_group_name = local.core_resource_group_name
}
