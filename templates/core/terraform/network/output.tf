output "core_vnet_id" {
  value = azurerm_virtual_network.core.id
}

output "bastion_subnet_id" {
  value = azurerm_subnet.bastion.id
}

output "azure_firewall_subnet_id" {
  value = azurerm_subnet.azure_firewall.id
}

output "app_gw_subnet_id" {
  value = azurerm_subnet.app_gw.id
}

output "web_app_subnet_id" {
  value = azurerm_subnet.web_app.id
}

output "shared_subnet_id" {
  value = azurerm_subnet.shared.id
}

output "resource_processor_subnet_id" {
  value = azurerm_subnet.resource_processor.id
}

output "azurewebsites_dns_zone_id" {
  value = azurerm_private_dns_zone.azurewebsites.id
}

output "static_web_dns_zone_id" {
  value = azurerm_private_dns_zone.static_web.id
}
