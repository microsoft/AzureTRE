resource "azurerm_route_table" "rt" {
  name                          = "rt-${var.tre_id}"
  resource_group_name           = azurerm_resource_group.core.name
  location                      = var.location
  disable_bgp_route_propagation = false

  lifecycle { ignore_changes = [tags] }

  route {
    name                   = "DefaultRoute"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = module.firewall.firewall_private_ip_address
  }
}

resource "azurerm_subnet_route_table_association" "rt_shared_subnet_association" {
  subnet_id      = module.network.shared_subnet_id
  route_table_id = azurerm_route_table.rt.id
}

resource "azurerm_subnet_route_table_association" "rt_resource_processor_subnet_association" {
  subnet_id      = module.network.resource_processor_subnet_id
  route_table_id = azurerm_route_table.rt.id
}

resource "azurerm_subnet_route_table_association" "rt_web_app_subnet_association" {
  subnet_id      = module.network.web_app_subnet_id
  route_table_id = azurerm_route_table.rt.id
}
