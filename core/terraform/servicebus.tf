resource "azurerm_servicebus_namespace" "sb" {
  name                = "sb-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  sku                 = "Premium"
  capacity            = "1"
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_servicebus_queue" "workspacequeue" {
  name         = "workspacequeue"
  namespace_id = azurerm_servicebus_namespace.sb.id

  enable_partitioning = false
  requires_session    = true # use sessions here to make sure updates to each resource happen in serial, in order
}

resource "azurerm_servicebus_queue" "service_bus_deployment_status_update_queue" {
  name         = "deploymentstatus"
  namespace_id = azurerm_servicebus_namespace.sb.id

  # The returned payload might be large, especially for errors.
  # Cosmos is the final destination of the messages where 2048 is the limit.
  max_message_size_in_kilobytes = 2048 # default=1024

  enable_partitioning = false
  requires_session    = true
}

resource "azurerm_private_dns_zone" "servicebus" {
  name                = "privatelink.servicebus.windows.net"
  resource_group_name = azurerm_resource_group.core.name
  tags                = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "servicebuslink" {
  name                  = "servicebuslink"
  resource_group_name   = azurerm_resource_group.core.name
  private_dns_zone_name = azurerm_private_dns_zone.servicebus.name
  virtual_network_id    = module.network.core_vnet_id
  tags                  = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "sbpe" {
  name                = "pe-sb-${var.tre_id}"
  location            = azurerm_resource_group.core.location
  resource_group_name = azurerm_resource_group.core.name
  subnet_id           = module.network.resource_processor_subnet_id
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group"
    private_dns_zone_ids = [azurerm_private_dns_zone.servicebus.id]
  }

  private_service_connection {
    name                           = "psc-sb-${var.tre_id}"
    private_connection_resource_id = azurerm_servicebus_namespace.sb.id
    is_manual_connection           = false
    subresource_names              = ["namespace"]
  }
}

# Block public access
# See https://docs.microsoft.com/azure/service-bus-messaging/service-bus-service-endpoints
resource "azurerm_servicebus_namespace_network_rule_set" "servicebus_network_rule_set" {
  namespace_id = azurerm_servicebus_namespace.sb.id
  ip_rules     = var.enable_local_debugging ? [local.myip] : null


  # We must enable the Airlock events subnet to access the SB, as the Eventgrid topics can't send messages over PE
  # https://docs.microsoft.com/en-us/azure/event-grid/consume-private-endpoints
  default_action                = "Deny"
  public_network_access_enabled = true
  network_rules {
    subnet_id                            = module.network.airlock_events_subnet_id
    ignore_missing_vnet_service_endpoint = false
  }

  # Allows the Eventgrid to access the SB
  trusted_services_allowed = true

  depends_on = [
    module.network
  ]
}

resource "azurerm_monitor_diagnostic_setting" "sb" {
  name                       = "diagnostics-sb-${var.tre_id}"
  target_resource_id         = azurerm_servicebus_namespace.sb.id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id
  # log_analytics_destination_type = "Dedicated"

  dynamic "enabled_log" {
    for_each = ["OperationalLogs", "VNetAndIPFilteringLogs", "RuntimeAuditLogs", "ApplicationMetricsLogs"]
    content {
      category = enabled_log.value

      retention_policy {
        enabled = true
        days    = 365
      }
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true

    retention_policy {
      enabled = true
      days    = 365
    }
  }
}
