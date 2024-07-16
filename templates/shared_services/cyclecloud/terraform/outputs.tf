output "connection_uri" {
  value = "https://${azurerm_private_dns_zone.cyclecloud.name}"
}
output "allowed_fqdns_list" {
  value = jsonencode(local.allowed_fqdns_list)
}
