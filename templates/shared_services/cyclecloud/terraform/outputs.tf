output "connection_uri" {
  value = "https://${azurerm_private_dns_zone.cyclecloud.name}"
}
