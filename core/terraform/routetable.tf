moved {
  from = azurerm_route_table.rt
  to   = module.network.azurerm_route_table.rt
}

moved {
  from = azurerm_route_table.fw_tunnel_rt
  to   = module.network.azurerm_route_table.fw_tunnel_rt
}

# Default route is added separately to avoid circular dependency between network and firewall modules
resource "azurerm_route" "default_route" {
  name                   = "DefaultRoute"
  resource_group_name    = azurerm_resource_group.core.name
  route_table_name       = module.network.route_table_name
  address_prefix         = "0.0.0.0/0"
  next_hop_type          = "VirtualAppliance"
  next_hop_in_ip_address = module.firewall.private_ip_address

  depends_on = [
    module.firewall,
    module.network
  ]
}
