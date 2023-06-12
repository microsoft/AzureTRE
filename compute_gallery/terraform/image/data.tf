data "azurerm_resource_group" "compute_gallery" {
  name = var.resource_group_name
}

data "azurerm_storage_share" "compute_gallery" {
  name                 = var.share_name
  storage_account_name = var.storage_account_name
}
