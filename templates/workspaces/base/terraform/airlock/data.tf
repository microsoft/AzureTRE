data "azurerm_user_assigned_identity" "airlock_id" {
  provider            = azurerm.core
  name                = "id-airlock-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_user_assigned_identity" "api_id" {
  provider            = azurerm.core
  name                = "id-api-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_private_dns_zone" "blobcore" {
  provider            = azurerm.core
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_namespace" "airlock_sb" {
  provider            = azurerm.core
  name                = "sb-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_topic" "blob_created" {
  provider     = azurerm.core
  name         = local.blob_created_topic_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id
}

data "azurerm_eventgrid_topic" "scan_result" {
  provider            = azurerm.core
  count               = var.enable_airlock_malware_scanning ? 1 : 0
  name                = local.airlock_malware_scan_result_topic_name
  resource_group_name = local.core_resource_group_name
}
