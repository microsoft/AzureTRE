# System topics

# Below we assign a SYSTEM-assigned identity for the topics. note that a user-assigned identity will not work.

resource "azurerm_eventgrid_system_topic" "import_approved_blob_created" {
  name                   = local.import_approved_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_import_approved.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  identity {
    type = "SystemAssigned"
  }

  tags = merge(
    var.tre_workspace_tags,
    {
      Publishers = "airlock;approved-import-sa"
    }
  )

  depends_on = [
    azurerm_storage_account.sa_import_approved
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_import_approved_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.import_approved_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.import_approved_blob_created
  ]
}

resource "azurerm_eventgrid_system_topic" "export_inprogress_blob_created" {
  name                   = local.export_inprogress_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_export_inprogress.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = merge(
    var.tre_workspace_tags,
    {
      Publishers = "airlock;inprogress-export-sa"
    }
  )

  identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_storage_account.sa_export_inprogress,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_export_inprogress_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_inprogress_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_inprogress_blob_created
  ]
}

resource "azurerm_eventgrid_system_topic" "export_rejected_blob_created" {
  name                   = local.export_rejected_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_export_rejected.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = merge(
    var.tre_workspace_tags,
    {
      Publishers = "airlock;rejected-export-sa"
    }
  )

  identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_storage_account.sa_export_rejected,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_export_rejected_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_rejected_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_rejected_blob_created
  ]
}

resource "azurerm_eventgrid_system_topic" "export_blocked_blob_created" {
  name                   = local.export_blocked_sys_topic_name
  location               = var.location
  resource_group_name    = var.ws_resource_group_name
  source_arm_resource_id = azurerm_storage_account.sa_export_blocked.id
  topic_type             = "Microsoft.Storage.StorageAccounts"

  tags = merge(
    var.tre_workspace_tags,
    {
      Publishers = "airlock;export-blocked-sa"
    }
  )

  identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_storage_account.sa_export_blocked,
  ]

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_export_blocked_blob_created" {
  scope                = data.azurerm_servicebus_namespace.airlock_sb.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_system_topic.export_blocked_blob_created.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_system_topic.export_blocked_blob_created
  ]
}

## Subscriptions
resource "azurerm_eventgrid_event_subscription" "import_approved_blob_created" {
  name  = "import-approved-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_import_approved.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.import_approved_blob_created,
    azurerm_role_assignment.servicebus_sender_import_approved_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_inprogress_blob_created" {
  name  = "export-inprogress-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_export_inprogress.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_inprogress_blob_created,
    azurerm_role_assignment.servicebus_sender_export_inprogress_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_rejected_blob_created" {
  name  = "export-rejected-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_export_rejected.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_rejected_blob_created,
    azurerm_role_assignment.servicebus_sender_export_rejected_blob_created
  ]
}

resource "azurerm_eventgrid_event_subscription" "export_blocked_blob_created" {
  name  = "export-blocked-blob-created-${var.short_workspace_id}"
  scope = azurerm_storage_account.sa_export_blocked.id

  service_bus_topic_endpoint_id = data.azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_system_topic.export_blocked_blob_created,
    azurerm_role_assignment.servicebus_sender_export_blocked_blob_created
  ]
}
