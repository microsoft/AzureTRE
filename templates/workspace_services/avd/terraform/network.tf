# Private endpoint for Host Pool
resource "azurerm_private_endpoint" "hostpool" {
  name                = "pe-${local.hostpool_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-${local.hostpool_name}"
    private_connection_resource_id = azurerm_virtual_desktop_host_pool.avd.id
    is_manual_connection           = false
    subresource_names              = ["connection"]
  }

  private_dns_zone_group {
    name                 = local.wvd_private_dns_zone_name
    private_dns_zone_ids = [data.azurerm_private_dns_zone.wvd.id]
  }

  lifecycle { ignore_changes = [tags] }
}

# Private endpoint for AVD Workspace (feed download)
resource "azurerm_private_endpoint" "workspace" {
  name                = "pe-${local.avd_workspace_name}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id
  tags                = local.workspace_service_tags

  private_service_connection {
    name                           = "psc-${local.avd_workspace_name}"
    private_connection_resource_id = azurerm_virtual_desktop_workspace.avd.id
    is_manual_connection           = false
    subresource_names              = ["feed"]
  }

  private_dns_zone_group {
    name                 = local.wvd_private_dns_zone_name
    private_dns_zone_ids = [data.azurerm_private_dns_zone.wvd.id]
  }

  lifecycle { ignore_changes = [tags] }
}
