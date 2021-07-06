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

data "azurerm_subnet" "services" {
  name                 = "ServicesSubnet"
  virtual_network_name = data.azurerm_virtual_network.ws.name
  resource_group_name  = data.azurerm_virtual_network.ws.resource_group_name
}

module "kv" {
  source       = "./keyvault"
  tre_id       = var.tre_id
  workspace_id = var.workspace_id
  service_id   = local.service_id
}

module "storage" {
  source       = "./storage"
  tre_id       = var.tre_id
  workspace_id = var.workspace_id
  service_id   = local.service_id
}

module "acr" {
  source       = "./acr"
  tre_id       = var.tre_id
  workspace_id = var.workspace_id
  service_id   = local.service_id
}

resource "azurerm_application_insights" "ai" {
  name                = "ai-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  application_type    = "web"

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_machine_learning_workspace" "ml" {
  name                    = local.workspace_name
  location                = data.azurerm_resource_group.ws.location
  resource_group_name     = data.azurerm_resource_group.ws.name
  application_insights_id = azurerm_application_insights.ai.id
  key_vault_id            = module.kv.keyvault_id
  storage_account_id      = module.storage.storage_account_id

  identity {
    type = "SystemAssigned"
  }

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone" "azureml" {
  name                = "privatelink.api.azureml.ms"
  resource_group_name = data.azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone" "azuremlcert" {
  name                = "privatelink.cert.api.azureml.ms"
  resource_group_name = data.azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [ tags ] }
}


resource "azurerm_private_dns_zone" "notebooks" {
  name                = "privatelink.notebooks.azure.net"
  resource_group_name = data.azurerm_resource_group.ws.name

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremllink" {
  name                  = "azuremllink-${local.service_resource_name_suffix}"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.azureml.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "azuremlcertlink" {
  name                  = "azuremlcertlink-${local.service_resource_name_suffix}"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.azuremlcert.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "notebookslink" {
  name                  = "notebookslink-${local.service_resource_name_suffix}"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.notebooks.name
  virtual_network_id    = data.azurerm_virtual_network.ws.id

  lifecycle { ignore_changes = [ tags ] }
}

resource "azurerm_private_endpoint" "mlpe" {
  name                = "mlpe-${local.service_resource_name_suffix}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  lifecycle { ignore_changes = [ tags ] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.azureml.id, azurerm_private_dns_zone.notebooks.id, azurerm_private_dns_zone.azuremlcert.id]
  }

  private_service_connection {
    name                           = "mlpesc-${local.service_resource_name_suffix}"
    private_connection_resource_id = azurerm_machine_learning_workspace.ml.id
    is_manual_connection           = false
    subresource_names              = ["amlworkspace"]
  }
}
