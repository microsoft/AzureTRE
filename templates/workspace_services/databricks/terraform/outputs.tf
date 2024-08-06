output "databricks_workspace_name" {
  value = azurerm_databricks_workspace.databricks.name
}

output "connection_uri" {
  value = "https://${azurerm_databricks_workspace.databricks.workspace_url}/aad/auth?has=&Workspace=${data.azurerm_subscription.current.id}/resourceGroups/${local.resource_group_name}/providers/Microsoft.Databricks/workspaces/${local.databricks_workspace_name}&WorkspaceResourceGroupUri=${data.azurerm_subscription.current.id}/resourceGroups/${local.managed_resource_group_name}&l=en-us"
}

output "databricks_storage_account_name" {
  value = azurerm_databricks_workspace.databricks.custom_parameters[0].storage_account_name
}

output "dbfs_blob_storage_domain" {
  value = replace("<stgacc>.blob.core.windows.net", "<stgacc>", azurerm_databricks_workspace.databricks.custom_parameters[0].storage_account_name)
}

output "log_blob_storage_domains" {
  value = local.map_location_url_config[module.azure_region.location_cli].logBlobStorageDomains
}

output "artifact_blob_storage_domains" {
  value = setunion(local.map_location_url_config[module.azure_region.location_cli].artifactBlobStoragePrimaryDomains, local.map_location_url_config[module.azure_region.location_cli].artifactBlobStorageSecondaryDomains)
}

output "workspace_address_spaces" {
  value = data.azurerm_virtual_network.ws.address_space
}

output "databricks_address_prefixes" {
  value = setunion(azurerm_subnet.container.address_prefixes, azurerm_subnet.host.address_prefixes)
}

# convert list of metastore domains to ip addresses
data "dns_a_record_set" "metastore_addresses" {
  for_each = toset(local.map_location_url_config[module.azure_region.location_cli].metastoreDomains)
  host     = each.key
}

output "metastore_addresses" {
  value = setunion(flatten([for addr in data.dns_a_record_set.metastore_addresses : addr.addrs]))
}

# convert list of event hub endpoint domains to ip addresses
data "dns_a_record_set" "event_hub_endpoint_addresses" {
  for_each = toset(local.map_location_url_config[module.azure_region.location_cli].eventHubEndpointDomains)
  host     = each.key
}

output "event_hub_endpoint_addresses" {
  value = setunion(flatten([for addr in data.dns_a_record_set.event_hub_endpoint_addresses : addr.addrs]))
}
