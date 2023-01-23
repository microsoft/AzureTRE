resource "azurerm_storage_account" "dbfs" {
  name                     = local.storage_name
  location                 = data.azurerm_resource_group.ws.location
  resource_group_name      = data.azurerm_resource_group.ws.name
  account_tier             = "Standard"
  account_replication_type = "GRS"
  tags                     = local.tre_workspace_service_tags
}
