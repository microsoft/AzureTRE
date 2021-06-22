terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.62.0"
    }
  }

  backend "azurerm" {
  }
}

provider "azurerm" {
  features {}
}

data "azurerm_resource_group" "ws" {
  name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_virtual_network" "ws" {
  name                = "vnet-${var.tre_id}-ws-${var.workspace_id}"
  resource_group_name = "rg-${var.tre_id}-ws-${var.workspace_id}"
}

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}


data "local_file" "dtl-vnet" {
  filename = "${path.module}/dtl.json"
}

resource "azurerm_template_deployment" "dtl" {
  name                = "dpl-${local.service_resource_name_suffix}"
  resource_group_name = data.azurerm_resource_group.ws.name

  template_body = data.local_file.dtl-vnet.content

  parameters = {
    "dtlName"  = "dtl-${local.service_resource_name_suffix}"
    "vnetId"   = data.azurerm_virtual_network.ws.id
    "vnetName" = data.azurerm_virtual_network.ws.name
  }

  deployment_mode = "Incremental"
}
