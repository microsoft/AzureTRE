output "ip" {
  value = azurerm_network_interface.internal.private_ip_address
}

output "hostname" {
  value = azurerm_windows_virtual_machine.windowsvm.name
}

output "azure_resource_id" {
  value = azurerm_windows_virtual_machine.windowsvm.id
}

output "connection_uri" {
  value = "https://${data.azurerm_linux_web_app.guacamole.default_hostname}/?/client/${textencodebase64("${azurerm_windows_virtual_machine.windowsvm.name}\u0000c\u0000azuretre", "UTF-8")}"
}

output "vm_username" {
  value = var.admin_username
}

output "vm_password_secret_name" {
  value = local.vm_password_secret_name
}

output "keyvault_name" {
  value = local.keyvault_name
}

# Exposed for callers that need to attach extra networking (e.g. the airlock
# export review VM's NSG rules).
output "nic_id" {
  value = azurerm_network_interface.internal.id
}

output "vm_private_ip_addresses" {
  value = azurerm_windows_virtual_machine.windowsvm.private_ip_addresses
}

output "resource_group_name" {
  value = data.azurerm_resource_group.ws.name
}

output "location" {
  value = data.azurerm_resource_group.ws.location
}

output "virtual_network_name" {
  value = data.azurerm_virtual_network.ws.name
}

output "short_workspace_id" {
  value = local.short_workspace_id
}

output "service_resource_name_suffix" {
  value = local.service_resource_name_suffix
}

output "tre_user_resources_tags" {
  value = local.tre_user_resources_tags
}
