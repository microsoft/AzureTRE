data "azurerm_storage_account" "sa_airlock_workspace_global" {
  provider            = azurerm.core
  name                = local.airlock_workspace_global_storage_name
  resource_group_name = local.core_resource_group_name
}

# ABAC restricts each private endpoint to containers for its workspace.
resource "azurerm_private_endpoint" "airlock_workspace_pe" {
  name                = "pe-sa-airlock-ws-global-${var.short_workspace_id}"
  location            = var.location
  resource_group_name = var.ws_resource_group_name
  subnet_id           = var.services_subnet_id
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }

  private_service_connection {
    name                           = "psc-sa-airlock-ws-global-${var.short_workspace_id}"
    private_connection_resource_id = data.azurerm_storage_account.sa_airlock_workspace_global.id
    is_manual_connection           = false
    subresource_names              = ["Blob"]
  }
}

# Per-workspace qualified zones prevent shared-hostname DNS collisions.
resource "azurerm_private_dns_zone" "airlock_workspace_global" {
  name                = "${local.airlock_workspace_global_storage_name}.${data.azurerm_private_dns_zone.blobcore.name}"
  resource_group_name = var.ws_resource_group_name
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_zone_virtual_network_link" "airlock_workspace_global" {
  name                  = "vnl-airlock-ws-global-${var.short_workspace_id}"
  resource_group_name   = var.ws_resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.airlock_workspace_global.name
  virtual_network_id    = var.workspace_vnet_id
  registration_enabled  = false
  tags                  = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_private_dns_a_record" "airlock_workspace_global" {
  name                = "@"
  zone_name           = azurerm_private_dns_zone.airlock_workspace_global.name
  resource_group_name = var.ws_resource_group_name
  ttl                 = 10
  records             = [azurerm_private_endpoint.airlock_workspace_pe.private_service_connection[0].private_ip_address]
  tags                = var.tre_workspace_tags

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_role_assignment" "api_workspace_global_blob_data_contributor" {
  provider = azurerm.core

  # Deterministic IDs prevent role-assignment collisions on the shared account.
  name                 = uuidv5("url", "${data.azurerm_storage_account.sa_airlock_workspace_global.id}-${var.workspace_id}-blob-data-contributor")
  scope                = data.azurerm_storage_account.sa_airlock_workspace_global.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azuread_service_principal.airlock_signer.object_id
  principal_type       = "ServicePrincipal"

  condition_version = "2.0"
  condition         = <<-EOT
    (
      (
        !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/add/action'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/delete'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/read'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/write'})
        AND !(ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/delete'})
      )
      OR
      (
        (
          ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/read'}
          OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/write'}
          OR ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/delete'}
        )
        AND
        @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:workspace_id]
          StringEquals '${var.workspace_id}'
      )
      OR
      (
        @Environment[Microsoft.Network/privateEndpoints] StringEqualsIgnoreCase
          '${azurerm_private_endpoint.airlock_workspace_pe.id}'
        AND
        @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:workspace_id]
          StringEquals '${var.workspace_id}'
        AND
        (
          @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:stage]
            StringEquals 'import-approved'
          OR
          @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:stage]
            StringEquals 'export-internal'
          OR
          (
            ActionMatches{'Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read'}
            AND
            @Resource[Microsoft.Storage/storageAccounts/blobServices/containers/metadata:stage]
              StringEquals 'export-in-progress'
          )
        )
      )
    )
  EOT
}
