output "connection_uri" {
  value = var.host_pool_type == "Pooled" ? "https://windows.cloud.microsoft/webclient/avd/${data.azapi_resource.avd_workspace.output.properties.objectId}/${one(data.azapi_resource_list.desktops.output.object_ids)}?tenant=${nonsensitive(data.azurerm_key_vault_secret.aad_tenant_id.value)}" : ""
}

output "hostpool_name" {
  value = azurerm_virtual_desktop_host_pool.avd.name
}

output "workspace_address_spaces" {
  value = jsonencode(data.azurerm_virtual_network.ws.address_space)
}
