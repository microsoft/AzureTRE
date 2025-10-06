data "azurerm_subscription" "current" {}

data "azurerm_client_config" "current" {}

# Random unique id
resource "random_string" "unique_id" {
  length      = 4
  min_numeric = 4
}

data "azurerm_container_registry" "mgmt_acr" {
  name                = var.acr_name
  resource_group_name = var.mgmt_resource_group_name
}

data "http" "myip" {
  count = var.public_deployment_ip_address == "" ? 1 : 0
  url   = "https://ipecho.net/plain"
}

data "azurerm_monitor_diagnostic_categories" "api" {
  resource_id = azurerm_linux_web_app.api.id
  depends_on = [
    azurerm_linux_web_app.api,
    azurerm_service_plan.core,
  ]
}

data "azurerm_key_vault" "core_kv" {
  name                = local.core_keyvault_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_key_vault_secret" "arm_client_id" {
  name         = local.arm_client_id
  key_vault_id = data.azurerm_key_vault.core_kv.id
}

data "azurerm_key_vault_secret" "arm_client_secret" {
  name         = local.arm_client_secret
  key_vault_id = data.azurerm_key_vault.core_kv.id
}
