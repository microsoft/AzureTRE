output "databricks_workspace_name" {
  value = azurerm_databricks_workspace.databricks.name
}

output "connection_uri" {
  value = "https://${azurerm_databricks_workspace.databricks.workspace_url}"
}

output "databricks_storage_account_name" {
  value = azurerm_databricks_workspace.databricks.custom_parameters[0].storage_account_name
}

output "dbfs_blob_storage_domain" {
  value = replace("<stgacc>.blob.core.windows.net", "<stgacc>", azurerm_databricks_workspace.databricks.custom_parameters[0].storage_account_name)
}

output "webapp_destination_addresses" {
  value = local.mapLocationUrlConfig[module.azure_region.location_cli].webappDestinationAddresses
}

output "extended_infrastructure_destination_addresses" {
  value = local.mapLocationUrlConfig[module.azure_region.location_cli].extendedInfrastructureDestinationAddresses
}

output "metastore_domains" {
  value = local.mapLocationUrlConfig[module.azure_region.location_cli].metastoreDomains
}

output "event_hub_endpoint_domains" {
  value = local.mapLocationUrlConfig[module.azure_region.location_cli].eventHubEndpointDomains
}

output "log_blob_storage_domains" {
  value = local.mapLocationUrlConfig[module.azure_region.location_cli].logBlobStorageDomains
}

output "artifact_blob_storage_domains" {
  value = setunion(local.mapLocationUrlConfig[module.azure_region.location_cli].artifactBlobStoragePrimaryDomains, local.mapLocationUrlConfig[module.azure_region.location_cli].artifactBlobStorageSecondaryDomains)
}

output "scc_relay_domains" {
  value = local.mapLocationUrlConfig[module.azure_region.location_cli].sccRelayDomains
}

output "workspace_address_spaces" {
  value = data.azurerm_virtual_network.ws.address_space
}

output "databricks_address_prefixes" {
  value = setunion(azurerm_subnet.private.address_prefixes, azurerm_subnet.public.address_prefixes)
}
