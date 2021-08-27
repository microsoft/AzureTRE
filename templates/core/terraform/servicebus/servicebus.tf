resource "azurerm_servicebus_namespace" "sb" {
  name                = "sb-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Premium"
  capacity            = "1"

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_servicebus_queue" "workspacequeue" {
  name                = "workspacequeue"
  resource_group_name = var.resource_group_name
  namespace_name      = azurerm_servicebus_namespace.sb.name

  enable_partitioning = false
}

resource "azurerm_servicebus_queue" "service_bus_deployment_status_update_queue" {
  name                = "deploymentstatus"
  resource_group_name = var.resource_group_name
  namespace_name      = azurerm_servicebus_namespace.sb.name

  enable_partitioning = false
}

resource "azurerm_private_dns_zone" "servicebus" {
  name                = "privatelink.servicebus.windows.net"
  resource_group_name = var.resource_group_name

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "servicebuslink" {
  name                  = "servicebuslink"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.servicebus.name
  virtual_network_id    = var.core_vnet

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_endpoint" "sbpe" {
  name                = "pe-sb-${var.tre_id}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.resource_processor_subnet_id

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

resource "azurerm_servicebus_namespace_network_rule_set" "servicebus_network_rule_set" {
  namespace_name      = azurerm_servicebus_namespace.sb.name
  resource_group_name = var.resource_group_name

  default_action = "Deny"

  network_rules {
    subnet_id                            = var.web_app_subnet_id
    ignore_missing_vnet_service_endpoint = false
  }

  network_rules {
    subnet_id                            = var.resource_processor_subnet_id
    ignore_missing_vnet_service_endpoint = false
  }
}

output "servicebus_namespace" {
  value = azurerm_servicebus_namespace.sb
}
