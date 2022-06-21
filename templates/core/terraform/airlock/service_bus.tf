# Utilize the existing service bus - add new queue
data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "sb-${var.tre_id}"
  resource_group_name = var.resource_group_name
}

resource "azurerm_servicebus_queue" "step_result" {
  name         = local.step_result_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "status_changed" {
  name         = local.status_changed_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "scan_result" {
  name         = local.scan_result_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_topic" "blob_created" {
  name         = local.blob_created_topic_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_subscription" "airlock_processor" {
  name               = local.blob_created_al_processor_subscription_name
  topic_id           = azurerm_servicebus_topic.blob_created.id
  max_delivery_count = 1
}

resource "azurerm_servicebus_subscription" "malware_scanner" {
  name               = local.blob_created_malware_subscription_name
  topic_id           = azurerm_servicebus_topic.blob_created.id
  max_delivery_count = 1
}



