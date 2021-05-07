# Azure Provider source and version being used
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=2.46.1"
    }
  }
}

resource "azurerm_resource_group" "workspace" {
  location = var.location
  name     = "${var.resource_group_prefix}-${var.tre_id}-${var.workspace_id}"
}

resource "azurerm_storage_account" "workspace" {
  name                      = local.storage_account_name
  resource_group_name       = azurerm_resource_group.workspace.name
  location                  = var.location
  access_tier               = "Hot"
  enable_https_traffic_only = true
  large_file_share_enabled  = false
  account_kind              = "StorageV2"
  account_tier              = "Standard"
  account_replication_type  = "LRS"

  network_rules {
    bypass         = ["AzureServices"]
    default_action = "Deny"

  }
}


resource "azurerm_private_endpoint" "workspace-storage-private-endpoint" {
  name                = "pe-wsstorage"
  resource_group_name = azurerm_resource_group.workspace.name
  location            = azurerm_resource_group.workspace.location
  subnet_id           = azurerm_subnet.services.id
  private_service_connection {
    private_connection_resource_id = azurerm_storage_account.workspace.id
    name                           = "pe-ws-storage"
    subresource_names              = ["file"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "privatelink.file.core.windows.net"
    private_dns_zone_ids = [azurerm_private_dns_zone.files.id]
  }
}

resource "azurerm_private_dns_zone" "files" {
  name                = "privatelink.file.core.windows.net"
  resource_group_name = azurerm_resource_group.workspace.name

}

resource "azurerm_private_dns_zone_virtual_network_link" "wsstorage" {
  resource_group_name   = azurerm_resource_group.workspace.name
  virtual_network_id    = azurerm_virtual_network.workspace.id
  private_dns_zone_name = azurerm_private_dns_zone.files.name
  name                  = "files-workspace-link"
  registration_enabled  = false
}
