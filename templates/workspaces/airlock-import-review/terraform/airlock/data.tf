data "azurerm_user_assigned_identity" "airlock_id" {
  name                = "id-airlock-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_user_assigned_identity" "api_id" {
  name                = "id-api-${var.tre_id}"
  resource_group_name = "rg-${var.tre_id}"
}

data "azurerm_private_dns_zone" "blobcore" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.blob.core.windows.net"]
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "sb-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_topic" "blob_created" {
  name                = local.blob_created_topic_name
  resource_group_name = local.core_resource_group_name
  namespace_name      = data.azurerm_servicebus_namespace.airlock_sb.name
  namespace_id        = data.azurerm_servicebus_namespace.airlock_sb.id
}
