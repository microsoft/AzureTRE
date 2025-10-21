locals {
  core_rt_name             = "rt-${var.tre_id}"
  core_rt_type             = "Microsoft.Network/routeTables"
  core_vng_name            = "vng-${var.tre_id}"
  core_vng_type            = "Microsoft.Network/virtualNetworkGateways"
  express_route_vng_name   = "exp-${var.tre_id}"
  express_route_circuit_id = "/subscriptions/f6cff649-c159-432a-bfb9-86c9249de4d1/resourceGroups/AGENCY-RG-000100/providers/Microsoft.Network/expressRouteCircuits/apazr-xr-uks"
  authorization_key        = {
    "cprddev"     = "6b48de5f-29b4-41b9-aa00-485acfc49209",
    "cprdtest"    = "6b26865b-fa38-4aea-a910-b3df0154393f",
    "cprdstaging" = "d4805db2-c19f-4d1d-9a73-abecebca335e",
    "cprdprod"    = "2011e837-20ae-4c1e-a5ce-8d51941b2bee"
  }
  next_hop_address_prefix = split(".", data.azurerm_subnet.azure_firewall.address_prefixes[0])
  next_hop_address        = join(".", [local.next_hop_address_prefix[0], local.next_hop_address_prefix[1], local.next_hop_address_prefix[2], "4"])
  tre_core_tags = {
    tre_id              = var.tre_id
    tre_core_service_id = var.tre_id
  }
}
