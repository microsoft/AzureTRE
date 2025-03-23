output "ip" {
  value = azurerm_network_interface.internal.private_ip_address
}

output "hostname" {
  value = azurerm_linux_virtual_machine.linuxvm.name
}

output "azure_resource_id" {
  value = azurerm_linux_virtual_machine.linuxvm.id
}

output "connection_uri" {
  value = "https://${data.azurerm_linux_web_app.guacamole.default_hostname}/?/client/${textencodebase64("${azurerm_linux_virtual_machine.linuxvm.name}\u0000c\u0000azuretre", "UTF-8")}"
}

output "vm_username" {
  value = local.admin_username
}

output "vm_password_secret_name" {
  value = local.vm_password_secret_name
}

output "keyvault_name" {
  value = local.keyvault_name
}

