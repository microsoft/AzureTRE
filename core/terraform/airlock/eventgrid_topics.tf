# Below we assign a SYSTEM-assigned identity for the topics. note that a user-assigned identity will not work.

# Event grid topics
resource "azurerm_eventgrid_topic" "step_result" {
  name                          = local.step_result_topic_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  public_network_access_enabled = var.enable_local_debugging
  local_auth_enabled            = false

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "Airlock Processor;"
  })

  inbound_ip_rule = var.enable_local_debugging ? [{
    ip_mask = var.myip
    action  = "Allow"
  }] : null

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_step_result" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_topic.step_result.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_topic.step_result
  ]
}

resource "azurerm_private_endpoint" "eg_step_result" {
  name                = "pe-eg-step-result-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_events_subnet_id
  tags                = var.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [var.eventgrid_private_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-eg-${var.tre_id}"
    private_connection_resource_id = azurerm_eventgrid_topic.step_result.id
    is_manual_connection           = false
    subresource_names              = ["topic"]
  }
}


resource "azurerm_eventgrid_topic" "status_changed" {
  name                          = local.status_changed_topic_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  public_network_access_enabled = var.enable_local_debugging
  local_auth_enabled            = false

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "TRE API;"
  })

  inbound_ip_rule = var.enable_local_debugging ? [{
    ip_mask = var.myip
    action  = "Allow"
  }] : null

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_status_changed" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_topic.status_changed.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_topic.status_changed
  ]
}

resource "azurerm_private_endpoint" "eg_status_changed" {
  name                = "pe-eg-status-changed-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_events_subnet_id
  tags                = var.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [var.eventgrid_private_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-eg-${var.tre_id}"
    private_connection_resource_id = azurerm_eventgrid_topic.status_changed.id
    is_manual_connection           = false
    subresource_names              = ["topic"]
  }
}

resource "azurerm_eventgrid_topic" "data_deletion" {
  name                          = local.data_deletion_topic_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  public_network_access_enabled = var.enable_local_debugging
  local_auth_enabled            = false

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "Airlock Processor;"
  })

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_data_deletion" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_topic.data_deletion.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_topic.data_deletion
  ]
}

resource "azurerm_private_endpoint" "eg_data_deletion" {
  name                = "pe-eg-data-deletion-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_events_subnet_id
  tags                = var.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [var.eventgrid_private_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-eg-${var.tre_id}"
    private_connection_resource_id = azurerm_eventgrid_topic.data_deletion.id
    is_manual_connection           = false
    subresource_names              = ["topic"]
  }
}

resource "azurerm_eventgrid_topic" "scan_result" {
  count               = var.enable_malware_scanning ? 1 : 0
  name                = local.scan_result_topic_name
  location            = var.location
  resource_group_name = var.resource_group_name
  # This is mandatory for the scan result to be published since private networks are not supported yet
  public_network_access_enabled = true
  local_auth_enabled            = false

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "Airlock Processor;"
  })

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_scan_result" {
  count                = var.enable_malware_scanning ? 1 : 0
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_topic.scan_result[0].identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_topic.scan_result
  ]
}

# System topic
# Custom topic (for airlock notifications)
resource "azurerm_eventgrid_topic" "airlock_notification" {
  name                          = local.notification_topic_name
  location                      = var.location
  resource_group_name           = var.resource_group_name
  public_network_access_enabled = var.enable_local_debugging
  local_auth_enabled            = false

  identity {
    type = "SystemAssigned"
  }

  tags = merge(var.tre_core_tags, {
    Publishers = "airlock;custom notification service;"
  })

  inbound_ip_rule = var.enable_local_debugging ? [{
    ip_mask = var.myip
    action  = "Allow"
  }] : null

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "servicebus_sender_airlock_notification" {
  scope                = var.airlock_servicebus.id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_eventgrid_topic.airlock_notification.identity[0].principal_id

  depends_on = [
    azurerm_eventgrid_topic.airlock_notification
  ]
}

resource "azurerm_private_endpoint" "eg_airlock_notification" {
  name                = "pe-eg-airlock_notification-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.airlock_events_subnet_id
  tags                = var.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [var.eventgrid_private_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-eg-${var.tre_id}"
    private_connection_resource_id = azurerm_eventgrid_topic.airlock_notification.id
    is_manual_connection           = false
    subresource_names              = ["topic"]
  }
}

## Subscriptions

resource "azurerm_eventgrid_event_subscription" "step_result" {
  name  = local.step_result_eventgrid_subscription_name
  scope = azurerm_eventgrid_topic.step_result.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.step_result.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_topic.step_result,
    azurerm_role_assignment.servicebus_sender_step_result
  ]
}
resource "azurerm_eventgrid_event_subscription" "status_changed" {
  name  = local.status_changed_eventgrid_subscription_name
  scope = azurerm_eventgrid_topic.status_changed.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.status_changed.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_topic.status_changed,
    azurerm_role_assignment.servicebus_sender_status_changed
  ]
}

resource "azurerm_eventgrid_event_subscription" "data_deletion" {
  name  = local.data_deletion_eventgrid_subscription_name
  scope = azurerm_eventgrid_topic.data_deletion.id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.data_deletion.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_topic.data_deletion,
    azurerm_role_assignment.servicebus_sender_data_deletion
  ]
}

resource "azurerm_eventgrid_event_subscription" "scan_result" {
  count = var.enable_malware_scanning ? 1 : 0
  name  = local.scan_result_eventgrid_subscription_name
  scope = azurerm_eventgrid_topic.scan_result[0].id

  service_bus_queue_endpoint_id = azurerm_servicebus_queue.scan_result.id

  delivery_identity {
    type = "SystemAssigned"
  }

  depends_on = [
    azurerm_eventgrid_topic.scan_result,
    azurerm_role_assignment.servicebus_sender_scan_result
  ]
}

# Unified EventGrid Event Subscription for ALL Core Blob Created Events
# This single subscription handles ALL 5 core stages: import-external, import-in-progress, 
# import-rejected, import-blocked, export-approved
resource "azurerm_eventgrid_event_subscription" "airlock_blob_created" {
  name  = "airlock-blob-created-${var.tre_id}"
  scope = azurerm_storage_account.sa_airlock_core.id

  service_bus_topic_endpoint_id = azurerm_servicebus_topic.blob_created.id

  delivery_identity {
    type = "SystemAssigned"
  }

  # Include all blob created events - airlock processor will check container metadata for routing
  included_event_types = ["Microsoft.Storage.BlobCreated"]

  depends_on = [
    azurerm_eventgrid_system_topic.airlock_blob_created,
    azurerm_role_assignment.servicebus_sender_airlock_blob_created
  ]
}

resource "azurerm_monitor_diagnostic_setting" "eventgrid_custom_topics" {
  for_each = merge({
    (azurerm_eventgrid_topic.airlock_notification.name) = azurerm_eventgrid_topic.airlock_notification.id,
    (azurerm_eventgrid_topic.step_result.name)          = azurerm_eventgrid_topic.step_result.id,
    (azurerm_eventgrid_topic.status_changed.name)       = azurerm_eventgrid_topic.status_changed.id,
    (azurerm_eventgrid_topic.data_deletion.name)        = azurerm_eventgrid_topic.data_deletion.id,
    },
    var.enable_malware_scanning ? { (azurerm_eventgrid_topic.scan_result[0].name) = azurerm_eventgrid_topic.scan_result[0].id } : null
  )

  name                       = "${each.key}-diagnostics"
  target_resource_id         = each.value
  log_analytics_workspace_id = var.log_analytics_workspace_id
  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.eventgrid_custom_topics.log_category_types
    content {
      category = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_monitor_diagnostic_setting" "eventgrid_system_topics" {
  for_each = {
    (azurerm_eventgrid_system_topic.airlock_blob_created.name)                  = azurerm_eventgrid_system_topic.airlock_blob_created.id,
    (azurerm_eventgrid_system_topic.airlock_workspace_global_blob_created.name) = azurerm_eventgrid_system_topic.airlock_workspace_global_blob_created.id,
  }

  name                       = "${each.key}-diagnostics"
  target_resource_id         = each.value
  log_analytics_workspace_id = var.log_analytics_workspace_id
  dynamic "enabled_log" {
    for_each = data.azurerm_monitor_diagnostic_categories.eventgrid_system_topics.log_category_types
    content {
      category = enabled_log.value
    }
  }

  enabled_metric {
    category = "AllMetrics"
  }
}
