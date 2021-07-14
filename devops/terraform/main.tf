provider "azurerm" {
  features {}
}

data "azurerm_client_config" "current" {}

#
# Core management resources
#
resource "azurerm_resource_group" "mgmt" {
  name     = var.mgmt_resource_group_name
  location = var.location

  lifecycle { ignore_changes = [ tags ] }
}


# Holds Terraform shared state (already exists, created by bootstrap.sh)
resource "azurerm_storage_account" "state_storage" {
  name                     = var.mgmt_storage_account_name
  resource_group_name      = azurerm_resource_group.mgmt.name
  location                 = azurerm_resource_group.mgmt.location
  account_tier             = "Standard"
  account_kind             = "StorageV2"
  account_replication_type = "LRS"
  allow_blob_public_access = false

  lifecycle { ignore_changes = [ tags ] }
}

#
# Shared container registry
#
resource "azurerm_container_registry" "shared_acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.mgmt.name
  location            = azurerm_resource_group.mgmt.location
  sku                 = var.acr_sku
  admin_enabled       = true

  lifecycle { ignore_changes = [ tags ] }
}