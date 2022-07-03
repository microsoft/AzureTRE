data "azurerm_service_plan" "core" {
  name                = "plan-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

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

data "local_file" "smtp-api-connection" {
  filename = "${path.module}/smtp-api-connection.json"
}

data "local_file" "smtp-access-policy" {
  filename = "${path.module}/smtp-access-policy.json"
}

data "azurerm_subscription" "current" {
}
