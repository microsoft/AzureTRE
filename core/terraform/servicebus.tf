resource "azurerm_servicebus_namespace" "sb" {
  name                         = "sb-${var.tre_id}"
  location                     = azurerm_resource_group.core.location
  resource_group_name          = azurerm_resource_group.core.name
  sku                          = "Premium"
  premium_messaging_partitions = "1"
  capacity                     = "1"
  local_auth_enabled           = false
  tags                         = local.tre_core_tags

  # Block public access
  # See https://docs.microsoft.com/azure/service-bus-messaging/service-bus-service-endpoints
  network_rule_set {
    ip_rules = var.enable_local_debugging ? [local.myip] : null

    # Allows the Eventgrid to access the SB
    trusted_services_allowed = true

    # We must enable the Airlock events subnet to access the SB, as the Eventgrid topics can't send messages over PE
    # https://docs.microsoft.com/en-us/azure/event-grid/consume-private-endpoints
    default_action                = "Deny"
    public_network_access_enabled = true
    network_rules {
      subnet_id                            = module.network.airlock_events_subnet_id
      ignore_missing_vnet_service_endpoint = false
    }
    network_rules {
      subnet_id                            = module.network.airlock_notification_subnet_id
      ignore_missing_vnet_service_endpoint = false
    }
  }

  dynamic "customer_managed_key" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      key_vault_key_id                  = azurerm_key_vault_key.tre_encryption[0].id
      identity_id                       = azurerm_user_assigned_identity.encryption[0].id
      infrastructure_encryption_enabled = true
    }
  }

  dynamic "identity" {
    for_each = var.enable_cmk_encryption ? [1] : []
    content {
      type         = "UserAssigned"
      identity_ids = [azurerm_user_assigned_identity.encryption[0].id]
    }
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_servicebus_queue" "workspacequeue" {
  name         = "workspacequeue"
  namespace_id = azurerm_servicebus_namespace.sb.id

  partitioning_enabled = false
  requires_session     = true # use sessions here to make sure updates to each resource happen in serial, in order
}

resource "azurerm_servicebus_queue" "service_bus_deployment_status_update_queue" {
  name         = "deploymentstatus"
  namespace_id = azurerm_servicebus_namespace.sb.id

  # The returned payload might be large, especially for errors.
  # Cosmos is the final destination of the messages where 2048 is the limit.
  max_message_size_in_kilobytes = 2048 # default=1024

  partitioning_enabled = false
  requires_session     = true
}

resource "azurerm_private_dns_zone" "servicebus" {
  name                = module.terraform_azurerm_environment_configuration.private_links["privatelink.servicebus.windows.net"]
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
  name                = "pe-${azurerm_servicebus_namespace.sb.name}"
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
    name                           = "psc-${azurerm_servicebus_namespace.sb.name}"
    private_connection_resource_id = azurerm_servicebus_namespace.sb.id
    is_manual_connection           = false
    subresource_names              = ["namespace"]
  }

  # private endpoints in serial
  depends_on = [
    azurerm_private_endpoint.filepe
  ]
}

resource "azurerm_monitor_diagnostic_setting" "sb" {
  name                       = "diagnostics-${azurerm_servicebus_namespace.sb.name}"
  target_resource_id         = azurerm_servicebus_namespace.sb.id
  log_analytics_workspace_id = module.azure_monitor.log_analytics_workspace_id

  dynamic "enabled_log" {
    for_each = setintersection(data.azurerm_monitor_diagnostic_categories.sb.log_category_types, local.servicebus_diagnostic_categories_enabled)
    content {
      category = enabled_log.value
    }
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }

  lifecycle { ignore_changes = [log_analytics_destination_type] }
}
