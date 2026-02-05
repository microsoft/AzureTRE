# Global Workspace Storage with workspace_id ABAC
# This file replaces storage_accounts.tf to use the global workspace storage account
# created in core infrastructure instead of creating a per-workspace account

# Data source to reference the global workspace storage account
data "azurerm_storage_account" "sa_airlock_workspace_global" {
  name                = local.airlock_workspace_global_storage_name
  resource_group_name = local.core_resource_group_name
}

# Data source to reference the global workspace EventGrid system topic
data "azurerm_eventgrid_system_topic" "airlock_workspace_global_blob_created" {
  name                = "evgt-airlock-blob-created-global-${var.tre_id}"
  resource_group_name = local.core_resource_group_name
}

# Private Endpoint for this workspace to access the global storage account
# Each workspace needs its own PE for network isolation
# ABAC will restrict this PE to only access containers with matching workspace_id
resource "azurerm_private_endpoint" "airlock_workspace_pe" {
  name                = "pe-sa-airlock-ws-global-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-sa-airlock-ws-global"
    private_dns_zone_ids = [data.azurerm_private_dns_zone.blobcore.id]
  }

  private_service_connection {
    name                           = "psc-sa-airlock-ws-global-${var.short_workspace_id}"
    private_connection_resource_id = data.azurerm_storage_account.sa_airlock_workspace_global.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

resource "azurerm_role_assignment" "api_workspace_global_blob_data_contributor" {
  scope                = data.azurerm_storage_account.sa_airlock_workspace_global.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_user_assigned_identity.api_id.principal_id

  condition_version = "2.0"
  condition         = <<-EOT
    (
      (
        !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})
      )
      OR
      (
        @Environment[Microsoft.Network/privateEndpoints] StringEqualsIgnoreCase
          '${azurerm_private_endpoint.airlock_workspace_pe.id}'
        AND
        @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['workspace_id']
          StringEquals '${var.workspace_id}'
        AND
        @Resource[Microsoft.Storage/storageAccounts/blobServices/containers].metadata['stage']
          StringIn ('import-approved', 'export-internal', 'export-in-progress')
      )
    )
  EOT
}
