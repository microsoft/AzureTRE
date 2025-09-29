resource "azurerm_route_table" "rt" {
  name                = "rt-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_route_table" "fw_tunnel_rt" {
  count                         = var.firewall_force_tunnel_ip != "" ? 1 : 0
  name                          = "rt-fw-tunnel-${var.tre_id}"
  resource_group_name           = var.resource_group_name
  location                      = var.location
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
