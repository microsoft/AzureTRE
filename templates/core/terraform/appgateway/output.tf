output "app_gateway_fqdn" {
  value = "https://${data.azurerm_public_ip.appgwpip_data.fqdn}"
}