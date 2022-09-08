# Azure Provider source and version being used
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
  name = "rg-${local.workspace_resource_name_suffix}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${local.workspace_resource_name_suffix}"
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
