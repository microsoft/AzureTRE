data "azurerm_application_insights" "core" {
  name                = "appi-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

data "azurerm_servicebus_namespace" "core" {
  name                = "sb-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}


data "azurerm_storage_account" "storage" {
  name                = local.storage_account_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_resource_group" "core" {
  name = local.core_resource_group_name
}

data "local_file" "smtp_api_connection" {
  filename = "${path.module}/smtp-api-connection.json"
}

data "local_file" "smtp_access_policy" {
  filename = "${path.module}/smtp-access-policy.json"
}

data "azurerm_subscription" "current" {
}

data "azurerm_eventgrid_topic" "airlock_notification" {
  name                = local.notification_topic_name
  resource_group_name = local.core_resource_group_name
}

data "azurerm_subnet" "airlock_notification" {
  name                 = "AirlockNotifiactionSubnet"
  virtual_network_name = local.core_vnet
  resource_group_name  = local.core_resource_group_name
}

data "azurerm_public_ip" "app_gateway_ip" {
  name                = "pip-agw-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}
