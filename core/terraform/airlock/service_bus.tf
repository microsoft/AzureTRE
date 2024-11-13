# Utilize the existing service bus - add new queue
resource "azurerm_servicebus_queue" "step_result" {
  name         = local.step_result_queue_name
  namespace_id = var.airlock_servicebus.id

  partitioning_enabled = false
}

resource "azurerm_servicebus_queue" "status_changed" {
  name         = local.status_changed_queue_name
  namespace_id = var.airlock_servicebus.id

  partitioning_enabled = false
}

resource "azurerm_servicebus_queue" "scan_result" {
  name         = local.scan_result_queue_name
  namespace_id = var.airlock_servicebus.id

  partitioning_enabled = false
}

resource "azurerm_servicebus_queue" "data_deletion" {
  name         = local.data_deletion_queue_name
  namespace_id = var.airlock_servicebus.id

  partitioning_enabled = false
}

resource "azurerm_servicebus_topic" "blob_created" {
  name         = local.blob_created_topic_name
  namespace_id = var.airlock_servicebus.id

  partitioning_enabled = false
}

resource "azurerm_servicebus_subscription" "airlock_processor" {
  name               = local.blob_created_al_processor_subscription_name
  topic_id           = azurerm_servicebus_topic.blob_created.id
  max_delivery_count = 1
}




