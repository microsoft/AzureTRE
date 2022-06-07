# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.0.0"
    }
    databricks = {
      source  = "databrickslabs/databricks"
      version = "0.5.9"
    }
    http = {
      source  = "hashicorp/http"
      version = "2.2.0"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {}
}

provider "http" {
}

data "azurerm_client_config" "current" {}

data "azurerm_resource_group" "rg" {
  name = local.resource_group_name
}

data "azurerm_virtual_network" "vnet" {
  name                = local.virtual_network_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_key_vault" "kv" {
  name                = local.keyvault_name
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_firewall" "firewall" {
  name                = local.firewall_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_public_ip" "firewall-public-ip" {
  name                = reverse(split("/", data.azurerm_firewall.firewall.ip_configuration.0.public_ip_address_id))[0]
  resource_group_name = local.core_resource_group_name
}

data "http" "myip" {
  url = "https://ifconfig.me"
}
