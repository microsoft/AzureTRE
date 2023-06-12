resource "azurerm_storage_account" "compute_gallery" {
  name                            = "stgcg${var.tre_id}"
  location                        = azurerm_resource_group.compute_gallery.location
  resource_group_name             = azurerm_resource_group.compute_gallery.name
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  allow_nested_items_to_be_public = false
  # tags                            = local.tre_core_tags
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "azurerm_storage_share" "compute_gallery" {
  name                 = "cvm-assets"
  storage_account_name = azurerm_storage_account.compute_gallery.name
  quota                = 1 # GB
}


