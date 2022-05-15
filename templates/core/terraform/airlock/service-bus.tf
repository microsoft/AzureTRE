resource "azurerm_servicebus_namespace" "airlock_sb" {
  name                = "airlock-sb-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Premium"
  capacity            = "1"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_servicebus_queue" "update_status_queue" {
  name         = "update_status_queue"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "status_changed_queue" {
  name         = "status_changed_queue"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "in_progress_import_queue" {
  name         = "in_progress_import_blob_created_queue"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "rejected_import_queue" {
  name         = "rejected_import_blob_created_queue"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}


resource "azurerm_servicebus_queue" "scan_result_queue" {
  name         = "scan_result_queue"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "accepted_import" {
  name         = "accepted_import_blob_created"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "inprogress_export" {
  name         = "inprogress_export_blob_created"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "rejected_export" {
  name         = "rejected_export_blob_created"
  namespace_id = azurerm_servicebus_namespace.airlock_sb.id

  enable_partitioning = false
}



