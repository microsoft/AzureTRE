data "azurerm_user_assigned_identity" "tre_encryption_identity" {
  count               = var.enable_cmk_encryption ? 1 : 0
  name                = local.encryption_identity_name
  resource_group_name = local.core_resource_group_name
}
