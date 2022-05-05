# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.97.0"
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
  name = "rg-${var.tre_id}-ws-${local.short_workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${local.short_workspace_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

data "azurerm_network_security_group" "ws" {
  name                = "nsg-ws"
  resource_group_name = data.azurerm_virtual_network.ws.resource_group_name
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

data "azurerm_app_service" "guacamole" {
  name                = "guacamole-${var.tre_id}-ws-${local.short_workspace_id}-svc-${local.short_parent_id}"
  resource_group_name = data.azurerm_resource_group.ws.name
}

output "ip" {
  value = azurerm_network_interface.internal.private_ip_address
}

output "hostname" {
  value = azurerm_linux_virtual_machine.linuxvm.name
}

output "azure_resource_id" {
  value = azurerm_linux_virtual_machine.linuxvm.id
}

output "connection_uri" {
  value = "https://${data.azurerm_app_service.guacamole.default_site_hostname}/?/client/${textencodebase64("${azurerm_linux_virtual_machine.linuxvm.name}\u0000c\u0000azuretre", "UTF-8")}"
}
