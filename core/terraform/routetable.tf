resource "azurerm_route_table" "rt" {
  name                          = "rt-${var.tre_id}"
  resource_group_name           = azurerm_resource_group.core.name
  location                      = var.location
  tags                          = local.tre_core_tags

  lifecycle { ignore_changes = [tags] }

  route {
    name                   = "DefaultRoute"
    address_prefix         = "0.0.0.0/0"
    next_hop_type          = "VirtualAppliance"
    next_hop_in_ip_address = module.firewall.private_ip_address
  }
}

resource "azurerm_subnet_route_table_association" "rt_shared_subnet_association" {
  subnet_id      = module.network.shared_subnet_id
  route_table_id = azurerm_route_table.rt.id

  depends_on = [
    module.firewall
  ]
}

resource "azurerm_subnet_route_table_association" "rt_resource_processor_subnet_association" {
  subnet_id      = module.network.resource_processor_subnet_id
  route_table_id = azurerm_route_table.rt.id

  # Not waiting for the rules will block traffic prematurally.
  depends_on = [
    module.firewall
  ]
}

resource "azurerm_subnet_route_table_association" "rt_web_app_subnet_association" {
  subnet_id      = module.network.web_app_subnet_id
  route_table_id = azurerm_route_table.rt.id

  depends_on = [
    module.firewall
  ]
}

resource "azurerm_subnet_route_table_association" "rt_airlock_processor_subnet_association" {
  subnet_id      = module.network.airlock_processor_subnet_id
  route_table_id = azurerm_route_table.rt.id

  depends_on = [
    module.firewall
  ]
}

resource "azurerm_subnet_route_table_association" "rt_airlock_storage_subnet_association" {
  subnet_id      = module.network.airlock_storage_subnet_id
  route_table_id = azurerm_route_table.rt.id

  depends_on = [
    module.firewall
  ]
}

resource "azurerm_subnet_route_table_association" "rt_airlock_events_subnet_association" {
  subnet_id      = module.network.airlock_events_subnet_id
  route_table_id = azurerm_route_table.rt.id

  depends_on = [
    module.firewall
  ]
}
