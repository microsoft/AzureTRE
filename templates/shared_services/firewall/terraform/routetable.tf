resource "azurerm_route_table" "rt" {
  name                          = "rt-${var.tre_id}"
  resource_group_name           = local.core_resource_group_name
  location                      = data.azurerm_resource_group.rg.location
  disable_bgp_route_propagation = false

  lifecycle { ignore_changes = [tags] }

  route {
    name                   = "DefaultRoute"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = azurerm_firewall.fw.ip_configuration.0.private_ip_address
  }
}

resource "azurerm_subnet_route_table_association" "rt_shared_subnet_association" {
  subnet_id      = data.azurerm_subnet.shared.id
  route_table_id = azurerm_route_table.rt.id
}

resource "azurerm_subnet_route_table_association" "rt_resource_processor_subnet_association" {
  subnet_id      = data.azurerm_subnet.resource_processor.id
  route_table_id = azurerm_route_table.rt.id
}

resource "azurerm_subnet_route_table_association" "rt_web_app_subnet_association" {
  subnet_id      = data.azurerm_subnet.web_app.id
  route_table_id = azurerm_route_table.rt.id
}
