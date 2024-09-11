data "azurerm_key_vault" "mgmt_kv" {
  count               = var.enable_cmk_encryption ? 1 : 0
  name                = var.kv_name
  resource_group_name = var.mgmt_resource_group_name
}