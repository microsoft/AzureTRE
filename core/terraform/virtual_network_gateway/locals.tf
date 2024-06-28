locals {
  core_rt_name            = "rt-${var.tre_id}"
  core_rt_type            = "Microsoft.Network/routeTables"
  core_vng_name           = "vng-${var.tre_id}"
  core_vng_type           = "Microsoft.Network/virtualNetworkGateways"
  next_hop_address_prefix = split(".", data.azurerm_subnet.azure_firewall.address_prefixes[0])
  next_hop_address        = join(".", [local.next_hop_address_prefix[0], local.next_hop_address_prefix[1], local.next_hop_address_prefix[2], "4"])
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }
}
