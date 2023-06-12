resource "azurerm_storage_share_directory" "scripts" {
  name                 = var.image_identifier
  share_name           = data.azurerm_storage_share.compute_gallery.name
  storage_account_name = var.storage_account_name
}

resource "azurerm_storage_share_file" "upload" {
  for_each         = toset(fileset(local.path_to_scripts, "*.*"))
  name             = each.value
  storage_share_id = data.azurerm_storage_share.compute_gallery.id
  path             = azurerm_storage_share_directory.scripts.name
  source           = "${local.path_to_scripts}/${each.value}"
}
