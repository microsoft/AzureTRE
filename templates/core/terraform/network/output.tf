output "core" {
  value = azurerm_virtual_network.core.id
}

output "bastion" {
  value = azurerm_subnet.bastion.id
}

output "azure_firewall" {
  value = azurerm_subnet.azure_firewall.id
}

output "app_gw" {
  value = azurerm_subnet.app_gw.id
}

output "web_app" {
  value = azurerm_subnet.web_app.id
}

output "shared" {
  value = azurerm_subnet.shared.id
}

output "aci" {
  value = azurerm_subnet.aci.id
}