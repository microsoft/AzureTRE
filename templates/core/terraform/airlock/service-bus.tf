# Utilize the existing service bus - add new queue
data "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "sb-${var.tre_id}"
  resource_group_name = var.resource_group_name

}

resource "azurerm_servicebus_queue" "update_status" {
  name         = local.update_status_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "status_changed" {
  name         = local.status_changed_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "import_in_progress_blob_created" {
  name         = local.import_inprogress_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "import_rejected_blob_created" {
  name         = local.import_rejected_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "scan_result" {
  name         = local.scan_result_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "import_approved_blob_created" {
  name         = local.import_approved_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "export_in_progress_blob_created" {
  name         = local.export_inprogress_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "export_rejected_blob_created" {
  name         = local.export_rejected_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

# Approved export
resource "azurerm_servicebus_queue" "export_approved_blob_created" {
  name         = local.export_approved_queue_name
  namespace_id = data.azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}



