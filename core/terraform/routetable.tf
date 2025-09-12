resource "azurerm_route_table" "fw_tunnel_rt" {
  count                         = var.firewall_force_tunnel_ip != "" ? 1 : 0
  name                          = "rt-fw-tunnel-${var.tre_id}"
  resource_group_name           = azurerm_resource_group.core.name
  location                      = azurerm_resource_group.core.location
  bgp_route_propagation_enabled = true
  tags                          = local.tre_core_tags
  lifecycle { ignore_changes = [tags] }

  route {
    name                   = "ForceTunnelRoute"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = var.firewall_force_tunnel_ip
  }
}

resource "azurerm_subnet_route_table_association" "rt_fw_tunnel_subnet_association" {
  count          = var.firewall_force_tunnel_ip != "" ? 1 : 0
  subnet_id      = module.network.azure_firewall_subnet_id
  route_table_id = azurerm_route_table.fw_tunnel_rt[0].id
}
