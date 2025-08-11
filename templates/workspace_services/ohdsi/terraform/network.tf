resource "azurerm_private_endpoint" "synapse_pe_workspace" {
  name                = "pe-synapse-ws-${local.short_workspace_id}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.services.id

  private_service_connection {
    name                           = "psc-synapse-ws-${local.short_workspace_id}"
    private_connection_resource_id = data.azurerm_synapse_workspace.synapse_cdm.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }
}

resource "azurerm_private_endpoint" "synapse_pe_core" {
  name                = "pe-synapse-core-${local.short_workspace_id}"
  location            = data.azurerm_resource_group.ws.location
  resource_group_name = data.azurerm_resource_group.ws.name
  subnet_id           = data.azurerm_subnet.resource_processor.id

  private_service_connection {
    name                           = "psc-synapse-core-${local.short_workspace_id}"
    private_connection_resource_id = data.azurerm_synapse_workspace.synapse_cdm.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }
}

resource "azurerm_private_dns_zone" "synapse_sql" {
  name                = "privatelink.sql.azuresynapse.net"
  resource_group_name = data.azurerm_resource_group.ws.name
}

resource "azurerm_private_dns_zone_virtual_network_link" "synapse_sql_link" {
  name                  = "synapse-sql-dns-link-ohdsi-omop"
  resource_group_name   = data.azurerm_resource_group.ws.name
  private_dns_zone_name = azurerm_private_dns_zone.synapse_sql.name
  virtual_network_id    = data.azurerm_virtual_network.core.id
  registration_enabled  = false
}

resource "azurerm_private_dns_a_record" "synapse_sql" {
  name                = "synapse-ws-omop-ohdsi-test"
  zone_name           = azurerm_private_dns_zone.synapse_sql.name
  resource_group_name = data.azurerm_resource_group.ws.name
  ttl                 = 300
  records             = [azurerm_private_endpoint.synapse_pe_core.private_service_connection[0].private_ip_address]
}