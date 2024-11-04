output "connection_uri" {
  value = "https://${azurerm_private_dns_zone.cyclecloud.name}"
}

output "shared_subnet_address_prefixes" {
  value = data.azurerm_subnet.shared.address_prefixes
}
