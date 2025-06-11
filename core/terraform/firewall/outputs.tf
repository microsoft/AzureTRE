output "private_ip_address" {
  value = azurerm_firewall.fw.ip_configuration[0].private_ip_address
}

output "firewall_policy_id" {
  value = azurerm_firewall_policy.root.id
}
