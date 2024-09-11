data "azurerm_client_config" "deployer" {}

data "azurerm_monitor_diagnostic_categories" "agw" {
  resource_id = azurerm_application_gateway.agw.id
  depends_on = [
    azurerm_application_gateway.agw
  ]
}

data "azurerm_key_vault" "mgmt_kv" {
  count               = var.enable_cmk_encryption ? 1 : 0
  name                = var.kv_name
  resource_group_name = var.mgmt_resource_group_name
}
