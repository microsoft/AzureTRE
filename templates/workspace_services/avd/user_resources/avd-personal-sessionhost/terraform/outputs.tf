output "ip" {
  value = azurerm_network_interface.sessionhost.private_ip_address
}

output "hostname" {
  value = azurerm_windows_virtual_machine.sessionhost.name
}

output "azure_resource_id" {
  value = azurerm_windows_virtual_machine.sessionhost.id
}

output "connection_uri" {
  value = "https://windows.cloud.microsoft/webclient/avd/${data.azapi_resource.avd_workspace.output.properties.objectId}/${data.azapi_resource.avd_desktop.output.properties.objectId}?tenant=${urlencode(var.auth_tenant_id)}&endpointId=${data.azapi_resource.avd_session_host.output.properties.objectId}"
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
