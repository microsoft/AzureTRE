resource "azurerm_storage_share" "HUE" {
  name                 = "huedata"
  storage_account_name = local.workspace_storage_name
//  quota                = var.HUE_storage_limit
}
